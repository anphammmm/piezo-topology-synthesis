"""The search loop.

Each round the model proposes up to `proposals_per_round` structures. Every new structure is
  1. screened: net power into a storage node fixed at 1.8 V, short runs, a few value presets
     (a necessary condition for vout_min, see screen.py); failures go back to the model with their powers;
  2. evaluated in full on the search conditions with the best preset's values;
  3. queued for sizing: an evolution strategy (sizer.py) runs generations while the model thinks.
Feedback to the model carries the measurements, the screen powers and physical hints (diagnostics.py).
Held-out conditions and the Monte Carlo robustness check run only after the search has stopped.
"""
from __future__ import annotations

import json
import random
import shutil
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from . import spec
from .bench import evaluate_circuit, evaluate_many
from .circuit import Circuit, CircuitError, describe, design_hash, parse_circuit, to_dict, topology_hash
from .diagnostics import codes, dead_v, hints, repeated
from .evaluate import Evaluation, diagnose, is_better
from .llm import LLMReply, proposals_from
from .netlist import build_netlist, reference_circuit
from .prompts import condition_table, iteration_prompt, repair_messages, system_prompt
from .records import Candidate, RunRecorder
from .refine import refine
from .robust import monte_carlo
from .screen import ScreenResult, screen
from .sim import Simulator
from .sizer import Sizer

__all__ = ["SearchConfig", "SearchOutcome", "run_search", "evaluate_circuit"]

SELECTABLE = ("llm", "size", "refine")


@dataclass
class SearchConfig:
    max_rounds: int = 12
    min_rounds: int = 3
    proposals_per_round: int = 3
    wall_clock_s: float = 3600
    max_sims: int = 0                 # simulation budget (0 = unlimited); equal budgets make runs comparable
    stagnation: int = 5               # rounds without improving the best proposed design
    screen: bool = True
    screen_presets: int = 4
    screen_alpha: float = 0.5
    screen_audit: bool = False        # also evaluate and size screen-rejected designs (filter calibration)
    sizer: str = "es"                 # es | coord | none
    size_budget: int = 48             # full evaluations per structure
    size_lambda: int = 8              # designs per sizing generation (simulated in parallel)
    size_min_gens: int = 1            # generations per model wait even if the model answers first
    drain_top: int = 2                # after the last round, finish sizing this many best structures
    diagnostics: bool = True
    mc_samples: int = 16              # Monte Carlo samples for the selected design (0 = skip)
    think: bool = True
    seed: int = 1
    continue_after_met: bool = False
    heartbeat_s: float = 15
    model_grace_s: float = 300        # a model call may run this long past wall_clock_s before it is abandoned


@dataclass
class SearchOutcome:
    selected: Candidate
    reference: Candidate
    stop_reason: str
    met_search: bool
    heldout_selected: Evaluation
    heldout_reference: Evaluation
    met_all: bool


@dataclass
class _Topo:
    topo_hash: str
    name: str
    root: Optional[Candidate] = None          # first full evaluation
    screen: Optional[ScreenResult] = None
    sizer: Optional[Sizer] = None
    best: Optional[Candidate] = None
    order: int = 0
    notes: List[str] = field(default_factory=list)

    def sizing_status(self) -> str:
        s = self.sizer
        if s is None:
            return ""
        state = "running" if not s.done else {"spec_met": "finished: spec met", "budget": "finished: budget used",
                                               "converged": "finished: converged",
                                               "no_parameters": "nothing to tune"}.get(s.reason, s.reason)
        return f"{s.n_evals}/{s.budget} evaluations ({state})"


class _Search:
    def __init__(self, cfg: SearchConfig, llm, sim: Simulator, rec: RunRecorder):
        self.cfg, self.llm, self.sim, self.rec = cfg, llm, sim, rec
        self.conds = spec.search_conditions()
        self.rng = random.Random(cfg.seed)
        self.candidates: List[Candidate] = []
        self.by_design: Dict[str, Candidate] = {}
        self.topos: Dict[str, _Topo] = {}
        self.best: Optional[Candidate] = None           # overall, the reference included
        self.best_found: Optional[Candidate] = None     # best proposed (or sized) design
        self.reference: Optional[Candidate] = None
        self.history: List[set] = []
        self.t = {"model_s": 0.0, "model_calls": 0, "prompt_tokens": 0, "completion_tokens": 0,
                  "reasoning_tokens": 0, "size_s": 0.0, "screen_s": 0.0, "model_errors": 0,
                  "n_screen_sims": 0, "n_proposals": 0, "n_screen_pass": 0, "n_invalid": 0, "n_duplicate": 0}
        self.iteration = 0

    # ---------------------------------------------------------------- bookkeeping
    def _new_candidate(self, c: Circuit, ev: Evaluation, origin: str, parent: Optional[str],
                       topo: Optional[_Topo] = None) -> Candidate:
        cand = Candidate(id=f"c{len(self.candidates):04d}", iteration=self.iteration, origin=origin,
                         parent=parent, circuit=c, topo_hash=topology_hash(c), design_hash=design_hash(c),
                         evaluation=ev, move=c.move if origin == "llm" else origin, name=c.name,
                         n_components=len(c.components))
        self.candidates.append(cand)
        self.by_design[cand.design_hash] = cand
        self.rec.candidate(cand)
        self.rec.event("candidate", id=cand.id, origin=origin, parent=parent, name=cand.name,
                       topo_hash=cand.topo_hash, scalar=round(ev.scalar, 4), cond_pass=ev.cond_pass,
                       checks_pass=ev.checks_pass, all_pass=ev.all_pass, n_sims=self.sim.stats["n_sims"])
        if topo is not None and (topo.best is None or is_better(ev, topo.best.evaluation, cand.n_components,
                                                                  topo.best.n_components)):
            topo.best = cand
        if origin in SELECTABLE:
            if self.best_found is None or is_better(ev, self.best_found.evaluation, cand.n_components,
                                                    self.best_found.n_components):
                self.best_found = cand
            if is_better(ev, self.best.evaluation, cand.n_components, self.best.n_components):
                self.best = cand
                self.rec.log("eval", f"new best {cand.id} ({cand.name}): score {ev.scalar:.2f}, "
                                     f"{ev.cond_pass}/{len(self.conds)} conditions pass")
        elif origin == "reference" and self.best is None:
            self.best = cand
        self._progress()
        return cand

    def _progress(self, **extra) -> None:
        b = self.best
        self.rec.progress(iteration=self.iteration, max_rounds=self.cfg.max_rounds,
                          best_id=b.id if b else None, best_name=b.name if b else None,
                          best_scalar=round(b.evaluation.scalar, 3) if b else None,
                          best_cond_pass=b.evaluation.cond_pass if b else None,
                          n_candidates=len(self.candidates), n_sims=self.sim.stats["n_sims"], **extra)

    def _budget_left(self) -> bool:
        if self.rec.elapsed() >= self.cfg.wall_clock_s:
            return False
        return not (self.cfg.max_sims and self.sim.stats["n_sims"] >= self.cfg.max_sims)

    def _budget_reason(self) -> str:
        return "time_budget" if self.rec.elapsed() >= self.cfg.wall_clock_s else "sim_budget"

    def _evaluate(self, c: Circuit, label: str) -> Evaluation:
        self.rec.progress(phase="sim")
        self.rec.log("sim", f"{label}: simulating {len(self.conds)} conditions")
        t = time.time()
        ev = evaluate_circuit(c, self.conds, self.sim, label)
        self.rec.log("eval", f"{label}: score {ev.scalar:.2f}, {ev.cond_pass}/{len(self.conds)} conditions, "
                             f"{ev.checks_pass}/{len(ev.checks)} checks pass ({time.time() - t:.1f} s)")
        return ev

    def _screen(self, c: Circuit, label: str, n_presets: Optional[int] = None) -> ScreenResult:
        self.rec.progress(phase="screen")
        t = time.time()
        before = self.sim.stats["n_sims"]
        r = screen(c, self.sim, self.rng, label, n_presets=n_presets or self.cfg.screen_presets,
                   alpha=self.cfg.screen_alpha)
        self.t["screen_s"] += time.time() - t
        self.t["n_screen_sims"] += self.sim.stats["n_sims"] - before
        self.rec.log("screen", f"{label}: {'PASS' if r.passed else 'fail'}, worst {r.worst_ratio * 100:.0f} % of "
                               f"the power needed ({r.n_presets} presets, {time.time() - t:.1f} s)")
        self.rec.event("screen", label=label, passed=r.passed, worst_ratio=r.worst_ratio, ratio=r.ratio,
                       gain=r.gain, p_net=r.p_net, n_presets=r.n_presets, sim_failed=r.sim_failed)
        return r

    def _account(self, reply: LLMReply) -> None:
        self.t["model_calls"] += 1
        self.t["model_s"] += reply.seconds or 0.0
        for k in ("prompt_tokens", "completion_tokens", "reasoning_tokens"):
            self.t[k] += getattr(reply, k) or 0
        if reply.error and reply.error != "spec_met_during_wait":
            self.t["model_errors"] += 1

    def _hints(self, ev: Optional[Evaluation], scr: Optional[ScreenResult]) -> List[str]:
        return [h.text for h in hints(ev, scr)] if self.cfg.diagnostics else []

    def _entry(self, cand: Candidate, topo: Optional[_Topo] = None) -> dict:
        ev = cand.evaluation
        topo = topo or self.topos.get(cand.topo_hash)
        scr = topo.screen if topo else None
        return {"id": cand.id, "name": cand.name, "topo_hash": cand.topo_hash, "scalar": ev.scalar,
                "cond_pass": ev.cond_pass, "circuit_text": describe(cand.circuit),
                "diagnosis": diagnose(ev), "table": condition_table(ev, self.conds),
                "screen": scr.summary() if scr else "", "sizing": topo.sizing_status() if topo else "",
                "hints": self._hints(ev, scr)}

    def _top(self, k: int = 4) -> List[dict]:
        ranked = sorted((t for t in self.topos.values() if t.best is not None),
                        key=lambda t: -t.best.evaluation.scalar)
        return [self._entry(t.best, t) for t in ranked[:k]]

    def _explored(self) -> List[dict]:
        return [{"topo_hash": t.topo_hash, "name": t.name,
                 "best_scalar": t.best.evaluation.scalar if t.best else float("nan")}
                for t in self.topos.values() if t.best is not None or t.screen is not None]

    # ---------------------------------------------------------------- sizing
    def _size_target(self) -> Optional[_Topo]:
        live = [t for t in self.topos.values() if t.sizer is not None and not t.sizer.done]
        if not live:
            return None
        return max(live, key=lambda t: (t.sizer.best_ev.scalar, t.order))

    def _size_generation(self, topo: _Topo, origin: str = "size") -> bool:
        sz = topo.sizer
        batch = sz.ask()
        if not batch:
            return False
        self.rec.progress(phase="size")
        t = time.time()
        evs = evaluate_many(batch, self.conds, self.sim,
                            [f"{topo.root.id}-size{sz.generations:02d}-{k}" for k in range(len(batch))])
        for c, ev in zip(batch, evs):
            self._new_candidate(c, ev, origin, topo.root.id, topo)
        before = sz.best_ev.scalar
        sz.tell(batch, evs)
        self.t["size_s"] += time.time() - t
        self.rec.log("size", f"{topo.root.id} ({topo.name}) generation {sz.generations}: best score "
                             f"{before:.2f} -> {sz.best_ev.scalar:.2f}, {sz.n_evals}/{sz.budget} evaluations "
                             f"({time.time() - t:.0f} s){'; ' + sz.reason if sz.done else ''}")
        return True

    def _coord(self, topo: _Topo, keep_going) -> None:
        """Ablation: the original coordinate search, run once per structure."""
        def ev_fn(c: Circuit) -> Evaluation:
            dh = design_hash(c)
            if dh in self.by_design:
                return self.by_design[dh].evaluation
            ev = evaluate_circuit(c, self.conds, self.sim, f"{topo.root.id}-coord")
            self._new_candidate(c, ev, "refine", topo.root.id, topo)
            return ev
        t = time.time()
        refine(topo.root.circuit, topo.root.evaluation, ev_fn, self.cfg.size_budget, self.rng,
               should_stop=lambda: not keep_going() or not self._budget_left())
        topo.sizer.done, topo.sizer.reason = True, "budget"
        self.t["size_s"] += time.time() - t

    def _met(self) -> bool:
        """The search has what it was looking for and should stop as soon as possible."""
        return (not self.cfg.continue_after_met and self.best_found is not None
                and self.best_found.evaluation.all_pass)

    def _size_while(self, keep_going) -> None:
        gens = 0
        while self._budget_left() and not self._met():
            if not keep_going() and gens >= self.cfg.size_min_gens:
                return
            topo = self._size_target()
            if topo is None:
                return
            if self.cfg.sizer == "coord":
                self._coord(topo, keep_going)
            elif not self._size_generation(topo):
                continue
            gens += 1

    # ---------------------------------------------------------------- model call
    def _ask(self, messages: List[dict], think: bool, attempt: int) -> LLMReply:
        holder: dict = {}
        deadline = self.cfg.wall_clock_s + self.cfg.model_grace_s      # in run-elapsed seconds
        budget = max(0.0, deadline - self.rec.elapsed())

        def call():
            try:
                holder["r"] = self.llm.ask(messages, think=think, timeout=budget)
            except Exception as e:   # the client should not raise, but never let the thread die silently
                holder["r"] = LLMReply(error=f"{type(e).__name__}: {e}")

        th = threading.Thread(target=call, daemon=True)
        t0 = time.time()
        self.rec.progress(phase="model", model_wait_s=0)
        self.rec.log("model", f"round {self.iteration}: asking the model (thinking {'on' if think else 'off'})")
        th.start()
        if attempt == 1:
            self._size_while(lambda: th.is_alive() and self.rec.elapsed() < deadline)
        last_beat = time.time()
        while th.is_alive():
            if self._met():
                # sizing met the spec while the model was thinking: stop waiting for an answer
                # that can no longer change the result (the daemon thread is abandoned)
                holder.setdefault("r", LLMReply(seconds=round(time.time() - t0, 1), error="spec_met_during_wait"))
                self.rec.log("model", "spec met while waiting; not waiting for the model's answer")
                break
            if self.rec.elapsed() >= deadline:
                holder.setdefault("r", LLMReply(seconds=round(time.time() - t0, 1),
                                                error="model call abandoned: wall-clock budget exceeded"))
                break
            th.join(timeout=min(1.0, self.cfg.heartbeat_s))
            if th.is_alive() and time.time() - last_beat >= self.cfg.heartbeat_s:
                last_beat = time.time()
                waited = time.time() - t0
                self.rec.progress(phase="model", model_wait_s=round(waited))
                self.rec.log("model", f"waiting {waited:.0f} s (round {self.iteration})")
        reply = holder.get("r") or LLMReply(error="model call abandoned: wall-clock budget exceeded")
        self._account(reply)
        self.rec.llm_exchange(self.iteration, attempt, messages, reply)
        tok = (f"{reply.prompt_tokens} in / {reply.completion_tokens} out" if reply.completion_tokens is not None
               else "no token counts")
        self.rec.log("model", f"reply after {reply.seconds:.0f} s ({tok})" + (f"; ERROR {reply.error}" if reply.error else ""))
        self.rec.event("model_reply", iteration=self.iteration, attempt=attempt, seconds=reply.seconds,
                       prompt_tokens=reply.prompt_tokens, completion_tokens=reply.completion_tokens,
                       reasoning_tokens=reply.reasoning_tokens, finish=reply.finish, error=reply.error)
        return reply

    @staticmethod
    def _parse_all(answer: str):
        """[(obj, circuit or None, problems)] and a flat list of problems for a repair request."""
        objs = proposals_from(answer)
        if objs is None:
            return [], ["no JSON object with a \"proposals\" list (or a circuit with \"components\") found"]
        out, flat = [], []
        for k, obj in enumerate(objs, 1):
            try:
                out.append((obj, parse_circuit(obj), []))
            except CircuitError as e:
                out.append((obj, None, e.problems))
                flat += [f"design {k} ({obj.get('name', '?')}): {p}" for p in e.problems]
        if not objs:
            flat.append("the proposals list is empty")
        return out, flat

    # ---------------------------------------------------------------- one proposal
    def _row(self, k: int, name: str, status: str, **extra) -> dict:
        row = {"round": self.iteration, "k": k, "name": name, "status": status, **extra}
        self.rec.proposal(row)
        return row

    def _process(self, k: int, obj: dict, circuit: Optional[Circuit], problems: List[str]) -> dict:
        rec, cfg = self.rec, self.cfg
        name = str(obj.get("name", "")) if isinstance(obj, dict) else ""
        self.t["n_proposals"] += 1
        if circuit is None:
            self.t["n_invalid"] += 1
            rec.event("proposal_invalid", iteration=self.iteration, k=k, problems=problems)
            self._row(k, name, "invalid", problems=" | ".join(problems)[:500])
            return {"kind": "invalid", "name": name, "invalid_problems": problems}
        th = topology_hash(circuit)
        if th in self.topos:
            prev = self.topos[th]
            self.t["n_duplicate"] += 1
            of = prev.root.id if prev.root else prev.name
            rec.event("duplicate", iteration=self.iteration, k=k, of=of, name=circuit.name)
            rec.log("eval", f"round {self.iteration} design {k} '{circuit.name}' repeats structure {of}; not simulated")
            self._row(k, circuit.name, "duplicate", move=circuit.move, topo_hash=th, of=of)
            return {"kind": "duplicate", "name": circuit.name, "id": of}
        topo = _Topo(th, circuit.name, order=len(self.topos))
        self.topos[th] = topo
        rec.event("proposal", iteration=self.iteration, k=k, move=circuit.move, name=circuit.name,
                  rationale=circuit.rationale, circuit=to_dict(circuit))
        rec.log("eval", f"round {self.iteration} design {k}: {circuit.move} '{circuit.name}' "
                        f"({len(circuit.components)} parts)")
        start = circuit
        scr_cols = {}
        if cfg.screen:
            scr = self._screen(circuit, f"r{self.iteration:02d}d{k}")
            topo.screen = scr
            scr_cols = {"worst_ratio": scr.worst_ratio, "n_presets": scr.n_presets,
                        **{f"ratio_{c}": v for c, v in scr.ratio.items()},
                        **{f"gain_{c}": v for c, v in scr.gain.items()}}
            if not scr.passed:
                hs = hints(None, scr)
                self.history.append(codes(hs))
                self._row(k, circuit.name, "screen_failed", move=circuit.move, topo_hash=th,
                          hints=" | ".join(h.code for h in hs), **scr_cols)
                if cfg.screen_audit:
                    self._audit(topo, scr.circuit)
                return {"kind": "screen_failed", "name": circuit.name, "topo_hash": th,
                        "screen": scr.summary(), "hints": self._hints(None, scr),
                        "circuit_text": describe(circuit)}
            self.t["n_screen_pass"] += 1
            start = scr.circuit
        ev = self._evaluate(start, f"r{self.iteration:02d}d{k}")
        cand = self._new_candidate(start, ev, "llm", None, topo)
        topo.root = cand
        hs = hints(ev, topo.screen)
        self.history.append(codes(hs))
        dead = any(h.code == "pinned" for h in hs) or not any(ev.sim_ok.values()) or \
            not any((m.get("vavg") or 0.0) >= dead_v() for m in ev.meas.values())
        if cfg.sizer != "none" and cfg.size_budget > 0 and not ev.all_pass and not dead:
            topo.sizer = Sizer(start, ev, cfg.size_budget, random.Random(self.rng.random()), lam=cfg.size_lambda)
        elif dead:
            rec.log("size", f"not sizing {cand.id} ({cand.name}): output never reaches {dead_v():g} V")
        self._row(k, circuit.name, "evaluated", move=circuit.move, topo_hash=th, candidate=cand.id,
                  hints=" | ".join(h.code for h in hs), **scr_cols)
        return dict(self._entry(cand, topo), kind="evaluated")

    def _audit(self, topo: _Topo, start: Circuit) -> None:
        """Filter calibration: evaluate and size a screen-rejected structure, outside the selection."""
        ev = evaluate_circuit(start, self.conds, self.sim, f"audit-{topo.topo_hash}")
        root = self._new_candidate(start, ev, "audit", None, None)
        sz = Sizer(start, ev, self.cfg.size_budget, random.Random(self.rng.random()), lam=self.cfg.size_lambda)
        tmp = _Topo(topo.topo_hash, topo.name, root=root, sizer=sz)
        while not sz.done and self._budget_left():
            if not self._size_generation(tmp, origin="audit"):
                break
        self.rec.event("audit", topo_hash=topo.topo_hash, name=topo.name, worst_ratio=topo.screen.worst_ratio,
                       met=sz.best_ev.all_pass, best_scalar=sz.best_ev.scalar, n_evals=sz.n_evals)
        self.rec.log("audit", f"screen-rejected '{topo.name}': best after sizing {sz.best_ev.scalar:.2f}, "
                              f"spec met: {sz.best_ev.all_pass}")

    # ---------------------------------------------------------------- main loop
    def run(self) -> SearchOutcome:
        cfg, rec = self.cfg, self.rec
        rec.write_json("spec.json", spec.spec_dict())
        rec.write_json("config.json", asdict(cfg))
        rec.progress(phase="setup", stop_reason=None)
        rec.log("setup", f"reference circuit on {len(self.conds)} search conditions")
        ref_c = reference_circuit()
        ref_c.move = "new_topology"
        self.reference = self._new_candidate(ref_c, self._evaluate(ref_c, "reference"), "reference", None)
        if cfg.screen:
            r = self._screen(ref_c, "reference", n_presets=1)
            rec.write_json("reference_screen.json", {"worst_ratio": r.worst_ratio, "ratio": r.ratio, "gain": r.gain,
                                                     "p_net": r.p_net, "p_req": r.p_req})
        system = system_prompt(self.reference.evaluation, per_round=cfg.proposals_per_round, screen=cfg.screen,
                               size_budget=cfg.size_budget)
        last: Optional[list] = None
        consecutive_errors = no_improve = 0
        stop_reason = "round_budget"
        for i in range(1, cfg.max_rounds + 1):
            self.iteration = i
            if not self._budget_left():
                stop_reason = self._budget_reason()
                break
            before = self.best_found.evaluation.scalar if self.best_found else None
            rep = repeated(self.history) if cfg.diagnostics else []
            user = iteration_prompt(i, cfg.max_rounds, self._top(), last, self._explored(), None, rep)
            messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
            reply = self._ask(messages, cfg.think, 1)
            done = False
            if self._met():
                stop_reason = "search_spec_met"
                break
            if reply.error:
                consecutive_errors += 1
                last = [{"kind": "error", "error": reply.error}]
                rec.event("model_error", iteration=i, error=reply.error)
            else:
                consecutive_errors = 0
                parsed, problems = self._parse_all(reply.answer)
                if not any(c is not None for _, c, _ in parsed):
                    rec.log("eval", f"round {i}: no usable design ({len(problems)} problems); asking for a correction")
                    rec.event("proposal_rejected", iteration=i, problems=problems)
                    if self._budget_left():
                        reply2 = self._ask(repair_messages(system, user, reply.answer, problems), False, 2)
                        if not reply2.error:
                            parsed2, problems2 = self._parse_all(reply2.answer)
                            if parsed2:
                                parsed, problems = parsed2, problems2
                if not parsed:
                    rec.event("proposal_invalid", iteration=i, problems=problems)
                    last = [{"kind": "invalid", "name": "", "invalid_problems": problems}]
                else:
                    last = []
                    for k, (obj, circuit, probs) in enumerate(parsed[:cfg.proposals_per_round], 1):
                        if not self._budget_left():
                            break
                        done = done or bool(circuit is not None and circuit.done)
                        last.append(self._process(k, obj, circuit, probs))
                        if self.best_found is not None and self.best_found.evaluation.all_pass:
                            break
            after = self.best_found.evaluation.scalar if self.best_found else None
            improved = after is not None and (before is None or after >= before + 0.01)
            no_improve = 0 if improved else no_improve + 1
            self._progress(phase="eval")
            if self.best_found is not None and self.best_found.evaluation.all_pass and not cfg.continue_after_met:
                stop_reason = "search_spec_met"
                break
            if done and i >= cfg.min_rounds:
                stop_reason = "model_done"
                break
            if consecutive_errors >= 3:
                stop_reason = "model_unavailable"
                break
            if no_improve >= cfg.stagnation and i >= cfg.min_rounds:
                stop_reason = "stagnation"
                break
            if not self._budget_left():
                stop_reason = self._budget_reason()
                break
        if stop_reason not in ("search_spec_met", "time_budget", "sim_budget"):
            self._drain()
        return self._finish(stop_reason)

    def _drain(self) -> None:
        """Finish sizing the few best structures once the model is no longer being asked."""
        live = sorted((t for t in self.topos.values() if t.sizer is not None and not t.sizer.done),
                      key=lambda t: -t.sizer.best_ev.scalar)[:self.cfg.drain_top]
        for topo in live:
            self.rec.log("size", f"finishing the sizing of {topo.root.id} ({topo.name})")
            while not topo.sizer.done and self._budget_left():
                if self.cfg.sizer == "coord":
                    self._coord(topo, lambda: True)
                elif not self._size_generation(topo):
                    break
                if self.best_found is not None and self.best_found.evaluation.all_pass:
                    return

    def _finish(self, stop_reason: str) -> SearchOutcome:
        rec = self.rec
        sel, ref = self.best, self.reference
        rec.log("done", f"search stopped: {stop_reason}; selected {sel.id} ({sel.name})")
        rec.event("stop", reason=stop_reason, selected=sel.id)
        held = spec.heldout_conditions()
        rec.progress(phase="heldout", stop_reason=stop_reason)
        rec.log("heldout", f"checking {sel.id} and the reference on {len(held)} held-out conditions")
        ev_sel = evaluate_circuit(sel.circuit, held, self.sim, f"{sel.id}-heldout")
        ev_ref = ev_sel if sel is ref else evaluate_circuit(ref.circuit, held, self.sim, "reference-heldout")
        pairs = [(sel, ev_sel)] if sel is ref else [(sel, ev_sel), (ref, ev_ref)]
        for cand, ev in pairs:
            rec.candidate(Candidate(**{**cand.__dict__, "evaluation": ev}), split="heldout")
        met_search = sel.evaluation.all_pass
        met_all = met_search and ev_sel.all_pass
        rec.log("heldout", f"{sel.id}: {ev_sel.cond_pass}/{len(held)} held-out conditions pass; "
                           f"reference: {ev_ref.cond_pass}/{len(held)}")
        if self.cfg.mc_samples > 0:
            rec.progress(phase="robust")
            rec.log("robust", f"Monte Carlo: {self.cfg.mc_samples} samples of {sel.id} on all {len(spec.CONDITIONS)} "
                              f"conditions")
            mc = monte_carlo(sel.circuit, spec.CONDITIONS, self.sim, random.Random(self.cfg.seed + 7919),
                             self.cfg.mc_samples, f"{sel.id}")
            rec.write_json("robust.json", {"candidate": sel.id, **mc})
            rec.log("robust", f"{mc['pass_all'] * 100:.0f} % of samples meet the spec on every condition; "
                              f"weakest: {mc['worst_condition']}")
        sdir = rec.out / "selected"
        if sdir.exists():
            shutil.rmtree(sdir)
        sdir.mkdir(parents=True)
        (sdir / "circuit.json").write_text(json.dumps(to_dict(sel.circuit), indent=1), encoding="utf-8")
        for cond in spec.CONDITIONS:
            (sdir / f"{cond.id}.net").write_text(build_netlist(sel.circuit, cond, title=sel.id), encoding="utf-8")
        st = self.sim.stats
        timing = {"wall_s": round(rec.elapsed(), 1), "model_s": round(self.t["model_s"], 1),
                  "model_calls": self.t["model_calls"], "model_errors": self.t["model_errors"],
                  "prompt_tokens": self.t["prompt_tokens"], "completion_tokens": self.t["completion_tokens"],
                  "reasoning_tokens": self.t["reasoning_tokens"],
                  "sim_seconds": round(st["sim_seconds"], 1), "sim_wall_s": round(st["wall_seconds"], 1),
                  "n_sims": st["n_sims"], "cache_hits": st["cache_hits"], "sim_failures": st.get("failures", 0),
                  "size_s": round(self.t["size_s"], 1), "screen_s": round(self.t["screen_s"], 1),
                  "n_screen_sims": self.t["n_screen_sims"], "n_proposals": self.t["n_proposals"],
                  "n_invalid": self.t["n_invalid"], "n_duplicate": self.t["n_duplicate"],
                  "n_topologies": len(self.topos), "n_screen_pass": self.t["n_screen_pass"],
                  "rounds": self.iteration,
                  "note": "model calls overlap sizing and simulations run in parallel, so the sums can exceed wall_s"}
        rec.timing(timing)
        failed = [{"split": split, **c.__dict__} for split, ev in (("search", sel.evaluation), ("heldout", ev_sel))
                  for c in ev.checks if not c.passed]
        first_met = next((e for e in self._events_met()), None)
        rec.write_json("outcome.json", {"stop_reason": stop_reason, "met_search": met_search, "met_all": met_all,
                                        "selected_id": sel.id, "selected_name": sel.name,
                                        "selected_origin": sel.origin, "reference_id": ref.id,
                                        "first_met": first_met, "failed_checks": failed})
        rec.progress(phase="done", stop_reason=stop_reason)
        rec.log("done", f"spec met on search conditions: {met_search}; on all conditions: {met_all}")
        return SearchOutcome(sel, ref, stop_reason, met_search, ev_sel, ev_ref, met_all)

    def _events_met(self):
        """When (time, simulations, round) the first spec-meeting proposed design appeared."""
        path = self.rec.out / "events.jsonl"
        if not path.exists():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("kind") == "candidate" and e.get("all_pass") and e.get("origin") in SELECTABLE:
                yield {"t": e.get("t"), "n_sims": e.get("n_sims"), "id": e.get("id")}


def run_search(cfg: SearchConfig, llm, sim: Simulator, rec: RunRecorder) -> SearchOutcome:
    return _Search(cfg, llm, sim, rec).run()
