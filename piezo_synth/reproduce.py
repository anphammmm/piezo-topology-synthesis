"""Re-simulate a saved circuit on chosen conditions, optionally keeping full waveforms.

    python3 -m piezo_synth.reproduce runs/<id>/selected/circuit.json --out runs/<id>/repro \
        --conditions all --waveforms
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from . import spec
from .circuit import parse_circuit
from .evaluate import evaluate
from .netlist import build_netlist
from .prompts import condition_table
from .sim import Simulator, ltspice_backend


def find_raw(folder):
    """The transient waveform file of a simulation folder (searched in subfolders too; .op.raw skipped)."""
    folder = Path(folder)
    if not folder.exists():
        return None
    raws = sorted(r for r in folder.rglob("*.raw") if not r.name.endswith(".op.raw"))
    return str(raws[0]) if raws else None


def pick_conditions(arg: str):
    if arg == "search":
        return spec.search_conditions()
    if arg == "heldout":
        return spec.heldout_conditions()
    if arg == "all":
        return list(spec.CONDITIONS)
    return [spec.condition(c.strip()) for c in arg.split(",") if c.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("circuit", help="circuit.json (e.g. runs/<id>/selected/circuit.json)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--conditions", default="all", help="search | heldout | all | comma list such as S1,H2")
    ap.add_argument("--waveforms", action="store_true", help="save all signals, uncompressed .raw")
    ap.add_argument("--fake", action="store_true", help="analytic stand-in for LTspice (dry run)")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args(argv)
    circ = parse_circuit(json.loads(Path(a.circuit).read_text(encoding="utf-8")))
    conds = pick_conditions(a.conditions)
    if a.fake:
        from .run import analytic_backend
        backend = analytic_backend
    else:
        backend = ltspice_backend()
    sim = Simulator(backend, Path(a.out), workers=a.workers, keep_raw=a.waveforms)
    jobs = []
    for cond in conds:
        text = build_netlist(circ, cond, title=f"reproduce {circ.name}")   # only the signals the plots use
        if a.waveforms:
            text = text.replace("\n.end\n", "\n.options plotwinsize=0\n.end\n")
        jobs.append((cond.id, text))
    results = sim.run(jobs)
    ev = evaluate({c.id: r for c, r in zip(conds, results)}, conds)
    print(condition_table(ev, conds), flush=True)
    waves = {}
    for cond, r in zip(conds, results):
        waves[cond.id] = find_raw(r.folder)
        if a.waveforms and waves[cond.id] is None:
            folder = Path(r.folder)
            listing = sorted(str(x.relative_to(folder)) for x in folder.rglob("*"))[:20] if folder.exists() else []
            print(f"{cond.id}: WARNING no .raw waveform file in {r.folder}; it contains: {listing}")
        if not r.ok:
            print(f"{cond.id}: simulation failed: {r.error[:300]}")
    (Path(a.out) / "reproduce.json").write_text(json.dumps({
        "circuit": a.circuit, "conditions": [c.id for c in conds], "all_pass": ev.all_pass,
        "checks": [asdict(c) for c in ev.checks], "meas": ev.meas, "raw_files": waves}, indent=1), encoding="utf-8")
    print(f"all pass: {ev.all_pass}; details in {Path(a.out) / 'reproduce.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
