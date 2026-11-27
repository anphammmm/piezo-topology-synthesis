"""The search loop: the model proposes, LTspice evaluates, feedback goes back; value tuning runs while
the model thinks. Held-out conditions are evaluated only after the search has stopped."""
from __future__ import annotations

import json
import random
import shutil
import threading
import time
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Set

from . import spec
from .circuit import Circuit, CircuitError, describe, design_hash, parse_circuit, to_dict, topology_hash
from .evaluate import Evaluation, diagnose, evaluate, is_better
from .llm import LLMReply, json_from
from .netlist import build_netlist, reference_circuit
from .prompts import condition_table, iteration_prompt, repair_messages, required_move, system_prompt
from .records import Candidate, RunRecorder
from .refine import refine
from .sim import Simulator


@dataclass
class SearchConfig:
    max_proposals: int = 16
    min_proposals: int = 4
    wall_clock_s: float = 3600
    stagnation: int = 6
    refine_budget: int = 10
    refine_min: int = 3          # tuning evaluations done even if the model replies quickly
    think: bool = True
    seed: int = 1
    continue_after_met: bool = False
    heartbeat_s: float = 15


@dataclass
class SearchOutcome:
    selected: Candidate
    reference: Candidate
    stop_reason: str
    met_search: bool
    heldout_selected: Evaluation
    heldout_reference: Evaluation
    met_all: bool


def evaluate_circuit(c: Circuit, conditions, sim: Simulator, label: str) -> Evaluation:
    jobs = [(f"{label}/{cond.id}", build_netlist(c, cond, title=label)) for cond in conditions]
    results = sim.run(jobs)
    return evaluate({cond.id: r for cond, r in zip(conditions, results)}, conditions)


class _Search:
    def __init__(self, cfg: SearchConfig, llm, sim: Simulator, rec: RunRecorder):
        self.cfg, self.llm, self.sim, self.rec = cfg, llm, sim, rec
        self.conds = spec.search_conditions()
        self.rng = random.Random(cfg.seed)
        self.candidates: List[Candidate] = []
        self.by_design: Dict[str, Candidate] = {}
        self.refined: Set[str] = set()
        self.best: Optional[Candidate] = None
        self.reference: Optional[Candidate] = None
        self.latest_llm: Optional[Candidate] = None
        self.moves: List[str] = []
        self.t = {"model_s": 0.0, "model_calls": 0, "prompt_tokens": 0, "completion_tokens": 0,
                  "reasoning_tokens": 0, "refine_s": 0.0, "model_errors": 0}
        self.iteration = 0

    # ---------------------------------------------------------------- bookkeeping
    def _new_candidate(self, c: Circuit, ev: Evaluation, origin: str, parent: Optional[str]) -> Candidate:
        cand = Candidate(id=f"c{len(self.candidates):04d}", iteration=self.iteration, origin=origin,
                         parent=parent, circuit=c, topo_hash=topology_hash(c), design_hash=design_hash(c),
                         evaluation=ev, move=c.move if origin == "llm" else origin, name=c.name,
                         n_components=len(c.components))
        self.candidates.append(cand)
        self.by_design[cand.design_hash] = cand
        self.rec.candidate(cand)
        self.rec.event("candidate", id=cand.id, origin=origin, parent=parent, name=cand.name,
                       topo_hash=cand.topo_hash, scalar=round(ev.scalar, 4), cond_pass=ev.cond_pass,
                       checks_pass=ev.checks_pass, all_pass=ev.all_pass)
        if origin != "reference" and is_better(ev, self.best.evaluation if self.best else None,
                                               cand.n_components, self.best.n_components if self.best else 0):
            self.best = cand
            self.rec.log("eval", f"new best {cand.id} ({cand.name}): score {ev.scalar:.2f}, "
                                 f"{ev.cond_pass}/{len(self.conds)} conditions pass")
        elif origin == "reference" and self.best is None:
            self.best = cand
        self._progress()
        return cand

    def _progress(self, **extra) -> None:
        b = self.best
        self.rec.progress(iteration=self.iteration, max_proposals=self.cfg.max_proposals,
                          best_id=b.id if b else None, best_name=b.name if b else None,
                          best_scalar=round(b.evaluation.scalar, 3) if b else None,
                          best_cond_pass=b.evaluation.cond_pass if b else None,
                          n_candidates=len(self.candidates), **extra)

    def _evaluate(self, c: Circuit, label: str) -> Evaluation:
        self.rec.progress(phase="sim")
        self.rec.log("sim", f"{label}: simulating {len(self.conds)} conditions")
        t = time.time()
        ev = evaluate_circuit(c, self.conds, self.sim, label)
        self.rec.log("eval", f"{label}: score {ev.scalar:.2f}, {ev.cond_pass}/{len(self.conds)} conditions, "
                             f"{ev.checks_pass}/{len(ev.checks)} checks pass ({time.time() - t:.1f} s)")
        return ev

    def _account(self, reply: LLMReply) -> None:
        self.t["model_calls"] += 1
        self.t["model_s"] += reply.seconds or 0.0
        for k in ("prompt_tokens", "completion_tokens", "reasoning_tokens"):
            self.t[k] += getattr(reply, k) or 0
        if reply.error:
            self.t["model_errors"] += 1

    def _entry(self, cand: Candidate) -> dict:
        ev = cand.evaluation
        return {"id": cand.id, "name": cand.name, "topo_hash": cand.topo_hash, "scalar": ev.scalar,
                "cond_pass": ev.cond_pass, "circuit_text": describe(cand.circuit),
                "diagnosis": diagnose(ev), "table": condition_table(ev, self.conds)}

    def _top(self, k: int = 5) -> List[dict]:
        best_per_topo: Dict[str, Candidate] = {}
        for c in self.candidates:
            if c.origin == "reference":
                continue
            cur = best_per_topo.get(c.topo_hash)
            if cur is None or is_better(c.evaluation, cur.evaluation, c.n_components, cur.n_components):
                best_per_topo[c.topo_hash] = c
        ranked = sorted(best_per_topo.values(), key=lambda c: -c.evaluation.scalar)
        return [self._entry(c) for c in ranked[:k]]

    def _explored(self) -> List[dict]:
        out: Dict[str, dict] = {}
        for c in self.candidates:
            if c.origin == "reference":
                continue
            e = out.setdefault(c.topo_hash, {"topo_hash": c.topo_hash, "name": c.name, "best_scalar": c.evaluation.scalar})
            e["best_scalar"] = max(e["best_scalar"], c.evaluation.scalar)
        return list(out.values())

    # ---------------------------------------------------------------- refinement
    def _refine_target(self) -> Optional[Candidate]:
        for c in (self.latest_llm, self.best):
            if c is not None and c.origin != "reference" and c.id not in self.refined:
                return c
        return None

    def _refine(self, target: Candidate, reply_arrived) -> None:
        self.refined.add(target.id)
        self.rec.progress(phase="refine")
        self.rec.log("refine", f"tuning values of {target.id} ({target.name}), up to {self.cfg.refine_budget} evaluations")
        t = time.time()
        count = {"n": 0}

        def ev_fn(c: Circuit) -> Evaluation:
            count["n"] += 1
            dh = design_hash(c)
            if dh in self.by_design:
                return self.by_design[dh].evaluation
            ev = evaluate_circuit(c, self.conds, self.sim, f"{target.id}-tune")
            self._new_candidate(c, ev, "refine", target.id)
            return ev

        def stop() -> bool:
            return reply_arrived() and count["n"] >= self.cfg.refine_min

        best_c, best_ev, tried = refine(target.circuit, target.evaluation, ev_fn, self.cfg.refine_budget,
                                        self.rng, should_stop=stop)
        self.t["refine_s"] += time.time() - t
        self.rec.log("refine", f"{target.id}: {len(tried)} evaluations, score {target.evaluation.scalar:.2f} -> "
                               f"{best_ev.scalar:.2f} ({time.time() - t:.0f} s)")

    # ---------------------------------------------------------------- model call
    def _ask(self, messages: List[dict], think: bool, attempt: int) -> LLMReply:
        holder: dict = {}

        def call():
            try:
                holder["r"] = self.llm.ask(messages, think=think)
            except Exception as e:   # the client should not raise, but never let the thread die silently
                holder["r"] = LLMReply(error=f"{type(e).__name__}: {e}")

        th = threading.Thread(target=call, daemon=True)
        t0 = time.time()
        self.rec.progress(phase="model", model_wait_s=0)
        self.rec.log("model", f"proposal {self.iteration}: asking the model (thinking {'on' if think else 'off'})")
        th.start()
        if attempt == 1:
            target = self._refine_target()
            if target is not None and self.cfg.refine_budget > 0:
                self._refine(target, lambda: not th.is_alive())
        last_beat = time.time()
        while th.is_alive():
            th.join(timeout=min(1.0, self.cfg.heartbeat_s))
            if th.is_alive() and time.time() - last_beat >= self.cfg.heartbeat_s:
                last_beat = time.time()
                waited = time.time() - t0
                self.rec.progress(phase="model", model_wait_s=round(waited))
                self.rec.log("model", f"waiting {waited:.0f} s (proposal {self.iteration})")
        reply = holder["r"]
        self._account(reply)
        self.rec.llm_exchange(self.iteration, attempt, messages, reply)
        tok = f"{reply.prompt_tokens} in / {reply.completion_tokens} out" if reply.completion_tokens is not None else "no token counts"
        self.rec.log("model", f"reply after {reply.seconds:.0f} s ({tok})" + (f"; ERROR {reply.error}" if reply.error else ""))
        self.rec.event("model_reply", iteration=self.iteration, attempt=attempt, seconds=reply.seconds,
                       prompt_tokens=reply.prompt_tokens, completion_tokens=reply.completion_tokens,
                       reasoning_tokens=reply.reasoning_tokens, finish=reply.finish, error=reply.error)
        return reply

    @staticmethod
    def _parse(answer: str):
        obj = json_from(answer)
        if obj is None:
            return None, ["no JSON object found in the reply"]
        try:
            return parse_circuit(obj), []
        except CircuitError as e:
            return None, e.problems

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
        system = system_prompt(self.reference.evaluation)
        last: Optional[dict] = None
        consecutive_errors = no_improve = 0
        stop_reason = "proposal_budget"
        for i in range(1, cfg.max_proposals + 1):
            self.iteration = i
            if rec.elapsed() >= cfg.wall_clock_s:
                stop_reason = "time_budget"
                break
            before = self.best.evaluation.scalar
            user = iteration_prompt(i, cfg.max_proposals, self._top(), last, self._explored(), required_move(self.moves))
            messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
            reply = self._ask(messages, cfg.think, 1)
            done = False
            if reply.error:
                consecutive_errors += 1
                last = {"error": reply.error}
                rec.event("model_error", iteration=i, error=reply.error)
            else:
                consecutive_errors = 0
                circuit, problems = self._parse(reply.answer)
                if problems:
                    rec.log("eval", f"proposal {i} rejected ({len(problems)} problems); asking for a correction")
                    rec.event("proposal_rejected", iteration=i, problems=problems)
                    reply2 = self._ask(repair_messages(system, user, reply.answer, problems), False, 2)
                    if not reply2.error:
                        circuit, problems = self._parse(reply2.answer)
                if circuit is None:
                    rec.event("proposal_invalid", iteration=i, problems=problems)
                    rec.log("eval", f"proposal {i} unusable: {'; '.join(problems)[:200]}")
                    last = {"invalid_problems": problems}
                else:
                    done = circuit.done
                    self.moves.append(circuit.move)
                    dh = design_hash(circuit)
                    if dh in self.by_design:
                        prev = self.by_design[dh]
                        rec.event("duplicate", iteration=i, of=prev.id, name=circuit.name)
                        rec.log("eval", f"proposal {i} duplicates {prev.id}; not simulated")
                        last = {"duplicate": True, "id": prev.id, "name": circuit.name}
                    else:
                        rec.event("proposal", iteration=i, move=circuit.move, name=circuit.name,
                                  rationale=circuit.rationale, circuit=to_dict(circuit))
                        rec.log("eval", f"proposal {i}: {circuit.move} '{circuit.name}' ({len(circuit.components)} parts)")
                        cand = self._new_candidate(circuit, self._evaluate(circuit, f"proposal-{i:02d}"), "llm", None)
                        self.latest_llm = cand
                        last = dict(self._entry(cand), duplicate=False, invalid_problems=[], refined_from=None)
            no_improve = 0 if self.best.evaluation.scalar >= before + 0.01 else no_improve + 1
            self._progress(phase="eval")
            if self.best.evaluation.all_pass and not cfg.continue_after_met:
                stop_reason = "search_spec_met"
                break
            if done and i >= cfg.min_proposals:
                stop_reason = "model_done"
                break
            if consecutive_errors >= 3:
                stop_reason = "model_unavailable"
                break
            if no_improve >= cfg.stagnation:
                stop_reason = "stagnation"
                break
            if rec.elapsed() >= cfg.wall_clock_s:
                stop_reason = "time_budget"
                break
        return self._finish(stop_reason)

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
        # selected design: circuit and the exact netlists for every condition
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
                  "refine_s": round(self.t["refine_s"], 1),
                  "note": "model calls overlap value tuning and simulations run in parallel, so the sums can exceed wall_s"}
        rec.timing(timing)
        failed = [{"split": split, **c.__dict__} for split, ev in (("search", sel.evaluation), ("heldout", ev_sel))
                  for c in ev.checks if not c.passed]
        rec.write_json("outcome.json", {"stop_reason": stop_reason, "met_search": met_search, "met_all": met_all,
                                        "selected_id": sel.id, "selected_name": sel.name,
                                        "selected_origin": sel.origin, "reference_id": ref.id,
                                        "failed_checks": failed})
        rec.progress(phase="done", stop_reason=stop_reason)
        rec.log("done", f"spec met on search conditions: {met_search}; on all conditions: {met_all}")
        return SearchOutcome(sel, ref, stop_reason, met_search, ev_sel, ev_ref, met_all)


def run_search(cfg: SearchConfig, llm, sim: Simulator, rec: RunRecorder) -> SearchOutcome:
    return _Search(cfg, llm, sim, rec).run()
