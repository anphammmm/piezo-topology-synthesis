"""Aggregate many runs (variants x seeds) and write the paper's tables.

    python -m piezo_synth.experiments runs/exp --paper paper/generated --smoke runs/smoke

Every run folder below the root that has outcome.json counts; its variant is the --label it was run
with (run_meta.json), else the name of its parent folder. Tables for which no data exist say
"pending" instead of showing numbers.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import spec

PENDING = r"\textit{pending: no runs yet}"

RUN_FIELDS = ["variant", "seed", "run", "stop_reason", "met_search", "met_all", "rounds", "n_proposals",
              "n_invalid", "n_duplicate", "n_topologies", "n_screen_pass", "n_sims", "n_screen_sims", "wall_s",
              "model_s", "model_calls", "prompt_tokens", "completion_tokens", "first_met_t", "first_met_sims",
              "heldout_pass", "mc_pass_all", "selected_name", "selected_origin"]


def _json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _heldout_pass(run: Path, cid: str) -> Optional[int]:
    path = run / "candidates.csv"
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("id") == cid and r.get("split") == "heldout":
                return int(r["cond_pass"])
    return None


def _run_row(run: Path) -> Optional[dict]:
    outcome = _json(run / "outcome.json")
    if not outcome or outcome.get("stop_reason") == "smoke":
        return None
    meta = _json(run / "run_meta.json", {}) or {}
    cfg = _json(run / "config.json", {}) or {}
    t = _json(run / "timing.json", {}) or {}
    rob = _json(run / "robust.json")
    fm = outcome.get("first_met") or {}
    row = {"variant": meta.get("label") or run.parent.name, "seed": meta.get("seed", cfg.get("seed")),
           "run": str(run), "stop_reason": outcome["stop_reason"], "met_search": bool(outcome["met_search"]),
           "met_all": bool(outcome["met_all"]), "first_met_t": fm.get("t"), "first_met_sims": fm.get("n_sims"),
           "heldout_pass": _heldout_pass(run, outcome["selected_id"]),
           "mc_pass_all": rob.get("pass_all") if rob else None,
           "selected_name": outcome.get("selected_name"), "selected_origin": outcome.get("selected_origin")}
    for k in ("rounds", "n_proposals", "n_invalid", "n_duplicate", "n_topologies", "n_screen_pass", "n_sims",
              "n_screen_sims", "wall_s", "model_s", "model_calls", "prompt_tokens", "completion_tokens"):
        row[k] = t.get(k)
    return row


def _median(xs) -> Optional[float]:
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def _mean(xs) -> Optional[float]:
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _audits(runs: List[Path]) -> Tuple[int, int]:
    """(screen-rejected structures audited, of which sizing still met the spec)."""
    n = met = 0
    for run in runs:
        p = run / "events.jsonl"
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("kind") == "audit":
                n += 1
                met += bool(e.get("met"))
    return n, met


def aggregate(root) -> Tuple[List[dict], List[dict]]:
    root = Path(root)
    run_dirs = sorted(p.parent for p in root.rglob("outcome.json")) if root.exists() else []
    runs = [r for r in (_run_row(d) for d in run_dirs) if r]
    by: Dict[str, List[dict]] = {}
    for r in runs:
        by.setdefault(r["variant"], []).append(r)
    summary = []
    for v, rs in sorted(by.items()):
        props = sum(r["n_proposals"] or 0 for r in rs)
        summary.append({
            "variant": v, "runs": len(rs),
            "success_rate": sum(r["met_search"] for r in rs) / len(rs),
            "met_all_rate": sum(r["met_all"] for r in rs) / len(rs),
            "median_sims_to_success": _median(r["first_met_sims"] for r in rs if r["met_search"]),
            "median_time_to_success_s": _median(r["first_met_t"] for r in rs if r["met_search"]),
            "median_sims": _median(r["n_sims"] for r in rs),
            "median_wall_s": _median(r["wall_s"] for r in rs),
            "mean_completion_tokens": _mean(r["completion_tokens"] for r in rs),
            "invalid_rate": (sum(r["n_invalid"] or 0 for r in rs) / props) if props else None,
            "screen_pass_rate": (sum(r["n_screen_pass"] or 0 for r in rs) /
                                 max(1, sum(r["n_topologies"] or 0 for r in rs))),
            "median_mc_pass": _median(r["mc_pass_all"] for r in rs),
            "mean_heldout_pass": _mean(r["heldout_pass"] for r in rs),
        })
    if root.exists():
        with (root / "experiments.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=RUN_FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(runs)
        if summary:
            with (root / "experiments_summary.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(summary[0]))
                w.writeheader()
                w.writerows(summary)
    return runs, summary


# ---------------------------------------------------------------- LaTeX

def tex(s) -> str:
    s = str(s)
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
                 ("_", r"\_"), ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\^{}")):
        s = s.replace(a, b)
    return s


def _num(v, fmt="{:.0f}", scale=1.0) -> str:
    return "--" if v is None else fmt.format(v * scale)


def _tabular(cols: str, head: List[str], rows: List[List[str]], ncols: int) -> str:
    lines = [r"\begin{tabular}{" + cols + "}", r"\toprule", " & ".join(head) + r" \\", r"\midrule"]
    if rows:
        lines += [" & ".join(r) + r" \\" for r in rows]
    else:
        lines.append(r"\multicolumn{" + str(ncols) + "}{c}{" + PENDING + r"} \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines) + "\n"


def _conditions_table() -> str:
    rows = [[c.id, "search" if c.split == "search" else "held-out", tex(c.label), f"{c.ip * 1e6:g}", f"{c.freq:g}",
             f"{c.cp * 1e9:g}", f"{c.rl / 1e3:g}", f"{c.temp:g}"] for c in spec.CONDITIONS]
    return _tabular("llp{3.2cm}rrrrr", ["ID", "Set", "Description", r"$I_p$ ($\mu$A)", "$f$ (Hz)", "$C_p$ (nF)",
                                        r"$R_L$ (k$\Omega$)", r"$T$ ($^\circ$C)"], rows, 8)


def _criteria_table() -> str:
    sym = {">=": r"$\geq$", "<=": r"$\leq$"}
    rows = [[tex(c.id), tex(c.meas), f"{sym[c.op]} {c.limit:g} {tex(c.unit)}", tex(c.description)] for c in spec.CRITERIA]
    return _tabular("llrp{5.2cm}", ["Criterion", "Measure", "Requirement", "Meaning"], rows, 4)


VARIANT_ORDER = ["full", "no_screen", "no_diag", "single", "coord", "no_think", "random"]


def _variants_table(summary: List[dict]) -> str:
    order = {v: k for k, v in enumerate(VARIANT_ORDER)}
    rows = []
    for s in sorted(summary, key=lambda s: order.get(s["variant"], 99)):
        rows.append([tex(s["variant"]), str(s["runs"]), _num(s["success_rate"], "{:.0f}\\%", 100),
                     _num(s["met_all_rate"], "{:.0f}\\%", 100), _num(s["median_sims_to_success"]),
                     _num(s["median_time_to_success_s"], "{:.0f}", 1 / 60), _num(s["median_sims"]),
                     _num(s["invalid_rate"], "{:.0f}\\%", 100), _num(s["median_mc_pass"], "{:.0f}\\%", 100)])
    return _tabular("lrrrrrrrr", ["Variant", "Runs", "Spec met", "+held-out", "Sims to success",
                                  "Min to success", "Sims", "Invalid", "MC pass"], rows, 9)


def _audit_table(n: int, met: int) -> str:
    rows = [[str(n), str(met), _num((n - met) / n if n else None, "{:.0f}\\%", 100)]] if n else []
    return _tabular("rrr", ["Rejected and audited", "Met spec after sizing", "Correct rejections"], rows, 3)


def _reference_table(smoke: Optional[Path]) -> str:
    """Reference (c0000) and witness (c0001) per condition, from a smoke-test run folder."""
    rows = []
    if smoke and (smoke / "measurements.csv").exists():
        with (smoke / "measurements.csv").open(newline="", encoding="utf-8") as f:
            meas = {(r["candidate"], r["condition"]): r for r in csv.DictReader(f)}
        passed: Dict[tuple, bool] = {}
        with (smoke / "checks.csv").open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                k = (r["candidate"], r["condition"])
                passed[k] = passed.get(k, True) and r["passed"].lower() == "true"
        for c in spec.CONDITIONS:
            cells = [c.id]
            for cid in ("c0000", "c0001"):
                m = meas.get((cid, c.id))
                if m is None or m.get("sim_ok", "").lower() != "true":
                    cells += ["--", "--", "--"]
                    continue
                v = float(m["vavg"]) if m.get("vavg") else None
                vmax = float(m["vmax"]) if m.get("vmax") else None
                cells += [_num(v, "{:.2f}"), _num(vmax, "{:.2f}"), "pass" if passed.get((cid, c.id)) else "fail"]
            rows.append(cells)
    return _tabular("l rrl rrl", ["Cond.", r"FBR $\bar V$", r"FBR $V_{max}$", "FBR", r"Witness $\bar V$",
                                   r"Witness $V_{max}$", "Witness"], rows, 7)


def _macros(summary: List[dict], runs: List[dict], audit: Tuple[int, int]) -> str:
    def m(name, val):
        return "\\newcommand{\\" + name + "}{" + (val if val is not None else r"\textbf{[pending]}") + "}\n"
    full = next((s for s in summary if s["variant"] == "full"), None)
    rnd = next((s for s in summary if s["variant"] == "random"), None)
    out = m("NRuns", str(len(runs)) if runs else None)
    out += m("FullSuccess", _num(full["success_rate"], "{:.0f}\\%", 100) if full else None)
    out += m("RandomSuccess", _num(rnd["success_rate"], "{:.0f}\\%", 100) if rnd else None)
    out += m("FullSimsToSuccess", _num(full["median_sims_to_success"]) if full else None)
    out += m("AuditN", str(audit[0]) if audit[0] else None)
    out += m("AuditMet", str(audit[1]) if audit[0] else None)
    return out


def write_paper_tables(gen_dir, root, smoke=None) -> None:
    gen = Path(gen_dir)
    gen.mkdir(parents=True, exist_ok=True)
    root = Path(root)
    runs, summary = aggregate(root)
    run_dirs = sorted(p.parent for p in root.rglob("outcome.json")) if root.exists() else []
    audit = _audits(run_dirs)
    files = {"tab_conditions.tex": _conditions_table(), "tab_criteria.tex": _criteria_table(),
             "tab_variants.tex": _variants_table(summary), "tab_screen_audit.tex": _audit_table(*audit),
             "tab_reference.tex": _reference_table(Path(smoke) if smoke else None),
             "macros.tex": _macros(summary, runs, audit)}
    for name, text in files.items():
        (gen / name).write_text(text, encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", help="folder holding the run folders (e.g. runs/exp)")
    ap.add_argument("--paper", help="write LaTeX tables into this folder (e.g. paper/generated)")
    ap.add_argument("--smoke", help="smoke-test run folder, for the reference/witness table")
    a = ap.parse_args(argv)
    runs, summary = aggregate(a.root)
    print(f"{len(runs)} runs, {len(summary)} variants")
    for s in summary:
        print(f"  {s['variant']:<10} runs {s['runs']:>2}  spec met {s['success_rate'] * 100:5.1f} %  "
              f"median sims to success {s['median_sims_to_success']}")
    if a.paper:
        write_paper_tables(a.paper, a.root, a.smoke)
        print(f"tables written to {a.paper}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
