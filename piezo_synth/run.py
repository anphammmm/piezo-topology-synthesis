"""Entry point for the cluster job.

    python3 -u -m piezo_synth.run --config run_config.json --out runs/<id>    full experiment
    python3 -u -m piezo_synth.run --smoke --out runs/smoke                   reference + witness, no model
    python3 -u -m piezo_synth.run --fake --out runs/dry                      wiring check without LTspice/Gemma
    python3 -u -m piezo_synth.run --baseline random --config c.json --out runs/<id>   model-free baseline
"""
from __future__ import annotations

import argparse
import json
import random
import math
import re
import shutil
import time
from dataclasses import fields
from pathlib import Path

from . import spec
from .circuit import design_hash, to_dict, topology_hash
from .evaluate import Evaluation
from .baselines import RandomProposer
from .llm import GemmaClient, ScriptedLLM
from .netlist import reference_circuit, spec_witness, witness_circuit
from .prompts import condition_table
from .records import Candidate, RunRecorder
from .report import build_report
from .screen import screen
from .search import SearchConfig, evaluate_circuit, run_search
from .sim import Simulator, ltspice_backend


# ---------------------------------------------------------------- dry-run stand-ins

class _FakeResult:
    def __init__(self, meas, folder):
        self.ok, self.meas, self.error, self.folder = True, meas, "", folder


def _uses(text: str, model: str) -> bool:
    return re.search(rf"^[DS]\w* .* {model}$", text, re.M) is not None


def analytic_backend(text: str, folder: str, timeout: float):
    """Plausible, deterministic numbers for a dry run (NOT a circuit simulation)."""
    Path(folder).mkdir(parents=True, exist_ok=True)
    (Path(folder) / "circuit.net").write_text(text, encoding="utf-8")
    ip = float(re.search(r"^Ipz pzn pzp SINE\(0 (\S+) (\S+)\)", text, re.M).group(1))
    if re.search(r"^Vst vsn 0 ", text, re.M):          # screening bench: net power at 1.8 V
        f = float(re.search(r"^Ipz pzn pzp SINE\(0 \S+ (\S+)\)", text, re.M).group(1))
        cp = float(re.search(r"^Cpz pzp pzn (\S+)$", text, re.M).group(1))
        p = (2.5 if _uses(text, "SWI") else 0.5) * ip ** 2 / (4 * math.pi ** 2 * f * cp)
        return _FakeResult({"isn": p * spec.SCREEN["rsense"] / spec.SCREEN["vstore"], "vout": spec.SCREEN["vstore"]}, folder)
    rl = float(re.search(r"^RL out 0 (\S+)$", text, re.M).group(1))
    boost = 2.5 if _uses(text, "SWI") else 1.0
    v = boost * (ip / 50e-6) * 2.2 * min(1.0, rl / 330e3) ** 0.3
    if _uses(text, "DZ33"):
        v = min(v, 3.35)
    meas = {"vavg": v, "vavg_prev": v - 0.005, "vpp": 0.02, "vmax": v * 1.02,
            "pload": v * v / rl, "pext": 1.3 * v * v / rl}
    if v > 1.85:
        meas["tup"] = 0.2
    return _FakeResult(meas, folder)


def _fake_replies() -> list:
    ref = to_dict(reference_circuit())
    clamp = dict(ref, name="bridge + zener clamp", move="modify_topology")
    clamp["components"] = ref["components"] + [{"id": "D5", "type": "D", "nodes": ["0", "out"], "model": "DZ33"}]
    sshi = dict(to_dict(witness_circuit()), name="p-SSHI + bridge + clamp", move="new_topology")
    dup = json.loads(json.dumps(sshi).replace('"n1"', '"mid"'))
    return [json.dumps(clamp), json.dumps(dup), json.dumps(sshi)]


# ---------------------------------------------------------------- smoke test

def screen_sign_suspect(scr: dict) -> bool:
    """True if the screen's sign looks wrong. A small negative net power for the reference on one
    condition is physical (S4: the open-circuit voltage is below 1.8 V plus two diode drops, so the bridge
    delivers nothing and the source loses the diodes' reverse leakage); the witness losing power, or the
    reference losing it on every condition, is not."""
    ref = [v for v in scr["reference"]["p_net"].values() if v is not None]
    wit = [v for v in scr["witness"]["p_net"].values() if v is not None]
    return any(v < 0 for v in wit) or (bool(ref) and all(v <= 0 for v in ref))


def run_smoke(sim: Simulator, rec: RunRecorder) -> None:
    """Reference and witness on all conditions: checks the simulator setup and the spec's difficulty."""
    rec.write_json("spec.json", spec.spec_dict())
    rec.write_json("config.json", {"mode": "smoke"})
    rec.progress(phase="sim", stop_reason=None)
    out = {}
    for k, (circ, origin) in enumerate(((reference_circuit(), "reference"), (spec_witness(), "witness"))):
        cid = f"c{k:04d}"
        for split, conds in (("search", spec.search_conditions()), ("heldout", spec.heldout_conditions())):
            rec.log("sim", f"{origin}: {len(conds)} {split} conditions")
            t = time.time()
            ev = evaluate_circuit(circ, conds, sim, f"{origin}-{split}")
            rec.log("eval", f"{origin} {split}: {ev.cond_pass}/{len(conds)} conditions pass ({time.time() - t:.1f} s)")
            print(condition_table(ev, conds), flush=True)
            rec.candidate(Candidate(cid, 0, origin, None, circ, topology_hash(circ), design_hash(circ), ev,
                                    origin, circ.name, len(circ.components)), split=split)
            out[(origin, split)] = ev
    ref_s1 = out[("reference", "search")].meas.get("S1", {})
    pext = ref_s1.get("pext")
    if pext is None or pext <= 0:
        rec.log("eval", f"WARNING: reference P_ext on S1 is {pext}; expected > 0. Check the sign of the pext "
                        f".meas in netlist.py before trusting P_ext columns.")
    wit_tup = [m.get("tup") for m in out[("witness", "search")].meas.values() if m.get("tup") is not None]
    if wit_tup and all(abs(t - spec.vmin()) < 1e-9 for t in wit_tup):
        rec.log("eval", f"WARNING: every t_up equals {spec.vmin():g}: ltspice_run is reading the threshold, not the crossing "
                        "time, from the 'tup' measurement line. Fix its parsing before the full run.")
    # the power screen on both circuits, with their own values: checks its sign and its calibration
    scr = {}
    for origin, circ in (("reference", reference_circuit()), ("witness", spec_witness())):
        r = screen(circ, sim, random.Random(1), f"{origin}-screen", n_presets=1)
        scr[origin] = {"passed": r.passed, "worst_ratio": r.worst_ratio, "ratio": r.ratio, "gain": r.gain,
                       "p_net": r.p_net, "p_req": r.p_req}
        rec.log("screen", f"{origin}: net power at {spec.SCREEN['vstore']:g} V vs need: {r.summary()}; "
                          f"gain over ideal FBR: " + ", ".join(f"{k} {v:.2f}" for k, v in r.gain.items() if v is not None))
    rec.write_json("smoke_screen.json", scr)
    if screen_sign_suspect(scr):
        rec.log("screen", "WARNING: net powers look sign-flipped (the witness loses power, or the reference loses "
                          "it everywhere): check the 'isn' measurement (V(out,vsn)) before trusting the screen.")
    if not scr["witness"]["passed"]:
        rec.log("screen", f"WARNING: the witness fails the screen (worst {scr['witness']['worst_ratio'] * 100:.0f} %); "
                          f"consider lowering screen_alpha.")
    ref_fail = [c for c in spec.search_conditions()
                if not all(ch.passed for ch in out[("reference", "search")].checks if ch.condition == c.id)]
    rec.log("eval", f"reference fails {len(ref_fail)}/{len(spec.search_conditions())} search conditions: {', '.join(c.id for c in ref_fail)} "
                    f"(the spec is meant to make it fail several)")
    st = sim.stats
    rec.timing({"wall_s": round(rec.elapsed(), 1), "model_s": 0, "model_calls": 0, "prompt_tokens": 0,
                "completion_tokens": 0, "reasoning_tokens": 0, "sim_seconds": round(st["sim_seconds"], 1),
                "sim_wall_s": round(st["wall_seconds"], 1), "n_sims": st["n_sims"], "cache_hits": st["cache_hits"],
                "refine_s": 0})
    rec.write_json("outcome.json", {"stop_reason": "smoke", "met_search": out[("witness", "search")].all_pass,
                                    "met_all": out[("witness", "search")].all_pass and out[("witness", "heldout")].all_pass,
                                    "selected_id": "c0001", "selected_name": spec_witness().name,
                                    "selected_origin": "witness", "reference_id": "c0000", "failed_checks": []})
    rec.progress(phase="done", stop_reason="smoke")


# ---------------------------------------------------------------- main

def load_config(path) -> SearchConfig:
    if not path:
        return SearchConfig()
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    known = {f.name for f in fields(SearchConfig)}
    unknown = sorted(set(raw) - known)
    if unknown:
        print(f"WARNING: ignoring unknown config keys: {', '.join(unknown)}", flush=True)
    return SearchConfig(**{k: v for k, v in raw.items() if k in known})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=f"runs/{time.strftime('%Y%m%d-%H%M%S')}")
    ap.add_argument("--config")
    ap.add_argument("--smoke", action="store_true", help="reference and witness only, no model")
    ap.add_argument("--fake", action="store_true", help="scripted model + analytic stand-in for LTspice")
    ap.add_argument("--baseline", choices=["random"], help="replace the model by a model-free proposer")
    ap.add_argument("--label", default="", help="variant name recorded in run_meta.json (for experiments.py)")
    ap.add_argument("--seed", type=int, help="overrides the config's seed")
    ap.add_argument("--spec", default="P1", choices=list(spec.SPECS), help="which specification (spec.SPECS)")
    ap.add_argument("--workers", type=int, default=8, help="parallel LTspice simulations")
    ap.add_argument("--sim-timeout", type=float, default=120.0, help="seconds per simulation")
    a = ap.parse_args(argv)
    with spec.using(a.spec):
        return _main(a, argv)


def _main(a, argv) -> int:
    out = Path(a.out)
    cfg = load_config(a.config)
    if a.seed is not None:
        cfg.seed = a.seed
    if a.fake:
        cfg.heartbeat_s = min(cfg.heartbeat_s, 1.0)
    backend = analytic_backend if a.fake else ltspice_backend()
    sim = Simulator(backend, out, workers=a.workers, timeout=a.sim_timeout)
    rec = RunRecorder(out)
    rec.write_json("run_meta.json", {"label": a.label, "baseline": a.baseline, "fake": a.fake, "smoke": a.smoke,
                                     "seed": cfg.seed, "spec": a.spec, "argv": argv})
    rec.log("setup", f"output in {out}; mode {'smoke' if a.smoke else 'search'}{' (fake)' if a.fake else ''}; spec {a.spec} ({spec.SPECS[a.spec].title})"
                     f"{' (baseline ' + a.baseline + ')' if a.baseline else ''}; "
                     f"{a.workers} parallel simulations")
    free = shutil.disk_usage(out).free / 2**30
    rec.log("setup", f"free disk where results go: {free:.1f} GiB")
    if free < 2:
        rec.log("setup", "WARNING: less than 2 GiB free; a full disk makes simulations fail. Free space first, "
                         "e.g. python3 tools/clean_raw.py runs --delete")
    try:
        if a.smoke:
            run_smoke(sim, rec)
        else:
            if a.baseline == "random":
                llm = RandomProposer(seed=cfg.seed, per_round=cfg.proposals_per_round)
            else:
                llm = ScriptedLLM(_fake_replies()) if a.fake else GemmaClient()
            run_search(cfg, llm, sim, rec)
    finally:
        build_report(out)
        rec.log("done", f"report: {out / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
