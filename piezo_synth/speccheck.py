"""Difficulty and feasibility check of every specification, without the language model.

    python3 -u -m piezo_synth.speccheck --out runs/speccheck            all specs (a cluster job)
    python3 -u -m piezo_synth.speccheck --specs P2,P3 --budget 96 --out runs/speccheck
    python3 -m piezo_synth.speccheck --fake --out /tmp/sc                 wiring check

For each spec it simulates, on the search and held-out conditions:
  reference  the full-bridge rectifier (expected to fail);
  textbook   the P1 witness, parallel SSHI + bridge + 3.3 V zener clamp, with its own values and after
             sizing by the same evolution strategy the search uses: the textbook answer at its best;
  witness    the spec's own hand-made circuit (netlist.spec_witness), also sized.
The verdict: "textbook_solves" (the spec does not need anything beyond the textbook circuit),
"witness_solves" (the textbook fails but a known-feasible design exists), or "unproven" (neither met it:
the spec may be infeasible with this vocabulary).
"""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path
from typing import List

from . import spec
from .bench import evaluate_circuit, evaluate_many
from .circuit import Circuit, to_dict
from .netlist import reference_circuit, spec_witness, witness_circuit
from .screen import screen
from .sim import Simulator, ltspice_backend
from .sizer import Sizer


def verdict(textbook_met: bool, witness_met: bool) -> str:
    if textbook_met:
        return "textbook_solves"
    return "witness_solves" if witness_met else "unproven"


def _size(c: Circuit, sim, budget: int, seed: int, label: str):
    conds = spec.search_conditions()
    ev = evaluate_circuit(c, conds, sim, f"{label}-proposed")
    sz = Sizer(c, ev, budget, random.Random(seed))
    k = 0
    while not sz.done:
        batch = sz.ask()
        if not batch:
            break
        evs = evaluate_many(batch, conds, sim, [f"{label}-g{k}-{i}" for i in range(len(batch))])
        sz.tell(batch, evs)
        k += 1
    return ev, sz


def _entry(c: Circuit, sim, budget: int, seed: int, label: str, size: bool) -> dict:
    held = spec.heldout_conditions()
    ev0 = evaluate_circuit(c, spec.search_conditions(), sim, f"{label}-search")
    d = {"name": c.name, "search_pass": ev0.cond_pass, "search_met": ev0.all_pass,
         "failed": sorted({ch.condition + ":" + ch.criterion for ch in ev0.checks if not ch.passed})}
    try:
        r = screen(c, sim, random.Random(seed), f"{label}-screen", n_presets=1)
        d["screen_ratio"] = r.ratio
    except Exception as e:  # noqa: BLE001 - a screen failure must not stop the check of the other specs
        d["screen_error"] = str(e)[:200]
    best = c
    if size:
        _, sz = _size(c, sim, budget, seed, label)
        best = sz.best
        d.update({"sized_search_pass": sz.best_ev.cond_pass, "sized_search_met": sz.best_ev.all_pass,
                  "sized_evals": sz.n_evals, "sizer_stop": sz.reason, "sized_circuit": to_dict(best),
                  "sized_failed": sorted({ch.condition + ":" + ch.criterion for ch in sz.best_ev.checks
                                          if not ch.passed})})
    evh = evaluate_circuit(best, held, sim, f"{label}-heldout")
    d.update({"heldout_pass": evh.cond_pass, "heldout_n": len(held)})
    return d


def check(name: str, root: Path, backend, budget: int, workers: int, seed: int) -> dict:
    with spec.using(name):
        out = root / name
        sim = Simulator(backend, out, workers=workers)
        t = time.time()
        print(f"[spec] {name}: {spec.SPECS[name].title}", flush=True)
        res = {"spec": name, "title": spec.SPECS[name].title, "hardness": spec.SPECS[name].hardness}
        res["reference"] = _entry(reference_circuit(), sim, budget, seed, "reference", size=False)
        res["textbook"] = _entry(witness_circuit(), sim, budget, seed, "textbook", size=True)
        w = spec_witness()
        if w.name != witness_circuit().name:
            res["witness"] = _entry(w, sim, budget, seed, "witness", size=True)
        else:
            res["witness"] = {"name": "(same as textbook)", **{k: v for k, v in res["textbook"].items() if k != "name"}}
        res["verdict"] = verdict(bool(res["textbook"].get("sized_search_met")),
                                 bool(res["witness"].get("sized_search_met")))
        res["n_sims"] = sim.stats["n_sims"]
        res["wall_s"] = round(time.time() - t, 1)
        out.mkdir(parents=True, exist_ok=True)
        (out / "summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
        tb, wi = res["textbook"], res["witness"]
        print(f"[spec] {name}: reference {res['reference']['search_pass']}/6; textbook {tb['search_pass']}/6 "
              f"-> sized {tb.get('sized_search_pass')}/6; witness sized {wi.get('sized_search_pass')}/6; "
              f"verdict {res['verdict']} ({res['n_sims']} sims, {res['wall_s']:.0f} s)", flush=True)
        return res


def _table(rows: List[dict]) -> str:
    lines = ["| spec | title | reference | textbook as given | textbook sized | witness sized | held-out (sized) "
             "| verdict |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        tb, wi = r["textbook"], r["witness"]
        best = wi if wi.get("sized_search_met") and not tb.get("sized_search_met") else tb
        lines.append(f"| {r['spec']} | {r['title']} | {r['reference']['search_pass']}/6 | {tb['search_pass']}/6 | "
                     f"{tb.get('sized_search_pass')}/6 | {wi.get('sized_search_pass')}/6 | "
                     f"{best.get('heldout_pass')}/{best.get('heldout_n')} | {r['verdict']} |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="runs/speccheck")
    ap.add_argument("--specs", default=",".join(spec.SPECS))
    ap.add_argument("--budget", type=int, default=96, help="sizing evaluations per circuit")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--fake", action="store_true", help="analytic stand-in for LTspice (NOT a simulation)")
    a = ap.parse_args(argv)
    root = Path(a.out)
    if a.fake:
        from .run import analytic_backend
        backend = analytic_backend
    else:
        backend = ltspice_backend()
    names = [n.strip() for n in a.specs.split(",") if n.strip()]
    rows = [check(n, root, backend, a.budget, a.workers, a.seed) for n in names]
    root.mkdir(parents=True, exist_ok=True)
    (root / "summary.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    (root / "speccheck.md").write_text("# Specification check\n\n" + _table(rows), encoding="utf-8")
    print(_table(rows), flush=True)
    print("[done] spec check written to", root / "speccheck.md", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
