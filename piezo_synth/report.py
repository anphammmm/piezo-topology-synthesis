"""Build report.md and summary.json from a run folder (works on incomplete runs too).

    python -m piezo_synth.report runs/<run_id>
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from . import spec as spec_mod
from .circuit import describe, parse_circuit


def _read_csv(path: Path, required=()) -> List[dict]:
    """Rows of a CSV; rows cut short by a killed or still-writing job (missing required fields) are skipped."""
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if all(r.get(k) not in (None, "") for k in required)]


def _read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _events(path: Path) -> List[dict]:
    out = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue   # a line cut off by a killed job
    return out


def _f(v, fmt="{:.3g}", scale=1.0) -> str:
    if v in (None, ""):
        return "-"
    try:
        return fmt.format(float(v) * scale)
    except ValueError:
        return str(v)


def _table(head: List[str], rows: List[List[str]]) -> str:
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(str(c).replace("|", "/") for c in r) + " |" for r in rows]
    return "\n".join(lines)


def _true(v) -> bool:
    return str(v).lower() in ("true", "1")


def build_report(out_dir) -> str:
    out = Path(out_dir)
    spec = _read_json(out / "spec.json") or spec_mod.spec_dict()
    cands = _read_csv(out / "candidates.csv", ("id", "split", "scalar", "n_components", "all_pass"))
    meas = _read_csv(out / "measurements.csv", ("candidate", "condition"))
    checks = _read_csv(out / "checks.csv", ("candidate", "condition", "criterion", "limit", "margin", "passed"))
    events = _events(out / "events.jsonl")
    timing = _read_json(out / "timing.json", {}) or {}
    outcome = _read_json(out / "outcome.json")
    progress = _read_json(out / "progress.json", {}) or {}
    crit_ids = [c["id"] for c in spec["criteria"]]
    conds = spec["conditions"]
    search_ids = [c["id"] for c in conds if c["split"] == "search"]
    held_ids = [c["id"] for c in conds if c["split"] == "heldout"]

    complete = outcome is not None and progress.get("phase") == "done"
    search_rows = [c for c in cands if c["split"] == "search"]
    if outcome:
        sel_id, ref_id = outcome["selected_id"], outcome["reference_id"]
        stop_reason = outcome["stop_reason"] if complete else "incomplete"
    else:
        stop_reason = "incomplete"
        ref_id = next((c["id"] for c in search_rows if c["origin"] == "reference"), None)
        others = [c for c in search_rows if c["origin"] != "reference"] or search_rows
        best = max(others, key=lambda c: (float(c["scalar"]), -int(c["n_components"])), default=None)
        sel_id = best["id"] if best else None
    by_id = {c["id"]: c for c in search_rows}
    sel = by_id.get(sel_id, {})

    M: Dict[tuple, dict] = {(m["candidate"], m["condition"]): m for m in meas}
    K: Dict[tuple, Dict[str, dict]] = defaultdict(dict)
    for k in checks:
        K[(k["candidate"], k["condition"])][k["criterion"]] = k

    def cond_rows(cid: str, ids: List[str]) -> List[List[str]]:
        rows = []
        for cond in ids:
            m = M.get((cid, cond))
            if m is None:
                continue
            ks = K.get((cid, cond), {})
            flags = ["ok" if _true(ks[c]["passed"]) else "**FAIL**" if c in ks else "-" for c in crit_ids]
            if not _true(m.get("sim_ok")):
                rows.append([cond, "sim failed", "", "", "", "", ""] + flags)
                continue
            rows.append([cond, _f(m["vavg"]), _f(m["vmax"]), _f(m["vpp"], scale=1e3), _f(m["tup"]),
                         _f(m["pload"], scale=1e6), _f(m["pext"], scale=1e6)] + flags)
        return rows

    mhead = ["cond", "Vavg V", "Vmax V", "ripple mV", "t_up s", "P_load uW", "P_ext uW"] + crit_ids

    def failed(cid: str, ids: List[str]) -> List[dict]:
        res = []
        for cond in ids:
            for c in crit_ids:
                k = K.get((cid, cond), {}).get(c)
                if k is not None and not _true(k["passed"]):
                    res.append({"condition": cond, "criterion": c, "measured": k["measured"] or None,
                                "op": k["op"], "limit": float(k["limit"]), "margin": float(k["margin"])})
        return res

    def all_pass(cid: str, ids: List[str]) -> bool:
        have = [K.get((cid, c)) for c in ids]
        return all(have) and not failed(cid, ids)

    s = ["# Piezoelectric harvester topology synthesis: run report", ""]
    s.append(f"Run folder: `{out}`. Stop reason: **{stop_reason}**. Selected design: **{sel_id}** "
             f"({sel.get('name', '?')}).")
    # 1. specification
    s += ["", "## Specification", "",
          "Every criterion must hold under every operating condition (0.8 s cold-start transient).", ""]
    s.append(_table(["criterion", "measurement", "requirement", "meaning"],
                    [[c["id"], c["meas"], f"{c['op']} {c['limit']:g} {c['unit']}", c["description"]]
                     for c in spec["criteria"]]))
    lim = spec["limits"]
    s += ["", f"Limits: at most {lim['max_components']} components, {lim['max_switches']} switches, "
              f"{lim['max_sync']} SYNC controllers (each draws {spec.get('ctrl_sink_a', 0.5e-6) * 1e6:g} uA from out); "
              f"L {lim['L'][0]:g}-{lim['L'][1]:g} H with series resistance {lim['l_rser_base']:g} Ohm + "
              f"{lim['l_rser_per_h'] / 1000:g} Ohm/mH; C up to {lim['C'][1]:g} F."]
    # 2. conditions
    s += ["", "## Test conditions", ""]
    s.append(_table(["id", "set", "description", "Ip uA pk", "f Hz", "Cp nF", "RL kOhm", "T C"],
                    [[c["id"], "search" if c["split"] == "search" else "held-out", c["label"], _f(c["ip"], scale=1e6),
                      _f(c["freq"]), _f(c["cp"], scale=1e9), _f(c["rl"], scale=1e-3), _f(c["temp"])] for c in conds]))
    s += ["", "Held-out conditions were never shown to the model and were not used for scoring, selection or stopping."]
    # 3. reference
    s += ["", "## Reference results", "",
          f"Reference: full-bridge rectifier, 4 x Schottky, 2.2 uF (candidate {ref_id})."]
    s += ["", _table(mhead, cond_rows(ref_id, search_ids + held_ids))] if ref_id else ["", "(not evaluated)"]
    # 4. proposals
    s += ["", "## Proposals tried", ""]
    props = _read_csv(out / "proposals.csv", ("round", "k", "status"))
    per_round: Dict[int, dict] = defaultdict(lambda: {"s": 0.0, "tok": 0, "calls": 0})
    for e in events:
        if e["kind"] == "model_reply":
            d = per_round[e["iteration"]]
            d["s"] += e.get("seconds") or 0
            d["tok"] += (e.get("completion_tokens") or 0)
            d["calls"] += 1
    screen_ids = list(spec.get("screen", {}).get("conditions", []))
    rows = []
    for p in props:
        c = by_id.get(p.get("candidate") or "", {})
        ratios = " ".join(f"{cid} {float(p['ratio_' + cid]) * 100:.0f} %" for cid in screen_ids
                          if p.get("ratio_" + cid) not in (None, "", "-inf"))
        if p["status"] == "invalid":
            detail = (p.get("problems") or "")[:120]
        elif p["status"] == "duplicate":
            detail = f"same as {p.get('of')}"
        else:
            detail = ratios
        rows.append([p["round"], p["k"], p.get("name", ""), p.get("move", ""), p.get("topo_hash", ""), p["status"],
                     detail, p.get("candidate") or "-",
                     f"{c['cond_pass']}/{len(search_ids)}" if c else "-", _f(c.get("scalar"), "{:.2f}") if c else "-",
                     p.get("hints") or "-"])
    s.append(_table(["round", "#", "name", "move", "topology", "outcome", "screen (power vs need) / detail",
                     "candidate", "cond. pass", "score", "problems found"], rows) if rows else "(none)")
    errors = [e for e in events if e["kind"] == "model_error"]
    if per_round:
        s += ["", "Model calls per round:", "",
              _table(["round", "calls", "model s", "completion tokens"],
                     [[r, d["calls"], f"{d['s']:.0f}", d["tok"] or "-"] for r, d in sorted(per_round.items())])]
    if errors:
        s += ["", f"{len(errors)} model call(s) failed: " + "; ".join(str(e.get("error"))[:80] for e in errors[:3])]
    rscreen = _read_json(out / "reference_screen.json")
    if rscreen:
        s += ["", "Reference on the screen (power delivered at 1.8 V vs need): " +
              ", ".join(f"{k} {v * 100:.0f} %" for k, v in sorted(rscreen.get("ratio", {}).items())) + "."]
    # 4b. sizing
    s += ["", "## Value sizing", ""]
    tuned = [c for c in search_rows if c["origin"] in ("size", "refine")]
    if tuned:
        grp: Dict[str, List[dict]] = defaultdict(list)
        for c in tuned:
            grp[c["parent"]].append(c)
        trows = []
        for p, v in grp.items():
            top = max(v, key=lambda x: float(x["scalar"]))
            trows.append([p, by_id.get(p, {}).get("name", ""), len(v), _f(by_id.get(p, {}).get("scalar"), "{:.2f}"),
                          _f(top["scalar"], "{:.2f}"), top["id"], f"{top['cond_pass']}/{len(search_ids)}"])
        s.append(_table(["structure (first evaluation)", "name", "evaluations", "start score", "best score",
                         "best candidate", "conditions passed"], trows))
    else:
        s.append("No structure was sized (none passed the screen with an output to tune, or sizing was off).")
    audits = [e for e in events if e["kind"] == "audit"]
    if audits:
        s += ["", "Screen audit (structures rejected by the screen, sized anyway to check the filter):", "",
              _table(["structure", "screen worst %", "evaluations", "best score", "spec met"],
                     [[a.get("name"), f"{(a.get('worst_ratio') or 0) * 100:.0f}", a.get("n_evals"),
                       _f(a.get("best_scalar"), "{:.2f}"), a.get("met")] for a in audits])]
    ntopo = len({c["topo_hash"] for c in search_rows if c["origin"] not in ("reference", "audit")})
    s += ["", f"{len(search_rows)} designs evaluated on the search conditions, {ntopo} distinct structures "
              f"(excluding the reference)."]
    # 5. selected design
    s += ["", "## Selected design", ""]
    circ = _read_json(out / "candidates" / str(sel_id) / "circuit.json") if sel_id else None
    if circ:
        try:
            text = describe(parse_circuit(circ))
        except Exception:   # an old or hand-edited file: show it raw
            text = json.dumps(circ, indent=1)
        s += [f"**{sel_id}**: {sel.get('name', '')} (origin {sel.get('origin', '?')}, topology {sel.get('topo_hash', '?')})",
              "", "```", text, "```", ""]
    s.append(_table(mhead, cond_rows(sel_id, search_ids)) if sel_id else "(none)")
    # 6. held-out
    s += ["", "## Held-out check", ""]
    if any((sel_id, c) in M for c in held_ids):
        s.append("Selected design:")
        s += ["", _table(mhead, cond_rows(sel_id, held_ids)), ""]
        if ref_id and ref_id != sel_id:
            s += ["Reference:", "", _table(mhead, cond_rows(ref_id, held_ids))]
    else:
        s.append("Not run (the search did not finish).")
    # 6b. robustness
    s += ["", "## Robustness", ""]
    rob = _read_json(out / "robust.json")
    if rob:
        tol = rob.get("tolerances", {})
        s.append(f"Monte Carlo on {rob.get('candidate')}: {rob['n']} samples, values drawn uniformly within "
                 f"R +/-{tol.get('R', 0) * 100:g} %, C +/-{tol.get('C', 0) * 100:g} %, L +/-{tol.get('L', 0) * 100:g} %, "
                 f"switch on-time +/-{tol.get('ton', 0) * 100:g} %, switch timing +/-{tol.get('phase', 0) * 100:g} % "
                 f"of a period. **{rob['pass_all'] * 100:.0f} %** of samples meet every criterion on every condition.")
        s += ["", _table(["condition", "samples passing"],
                         [[k, f"{v * 100:.0f} %"] for k, v in rob.get("per_condition", {}).items()])]
    else:
        s.append("Not run.")
    # 7. unmet
    fails = [dict(f, split="search") for f in failed(sel_id, search_ids)] + \
            [dict(f, split="heldout") for f in failed(sel_id, held_ids)] if sel_id else []
    s += ["", "## Unmet requirements", ""]
    if fails:
        s.append(_table(["set", "condition", "criterion", "measured", "requirement", "margin"],
                        [[f["split"], f["condition"], f["criterion"],
                          _f(f["measured"]) if f["measured"] else "not reached", f"{f['op']} {f['limit']:g}",
                          f"{f['margin']:+.2f}"] for f in fails]))
    else:
        s.append("None: the selected design meets every criterion on every evaluated condition.")
    met_search = bool(sel_id) and all_pass(sel_id, search_ids)
    met_all = met_search and all_pass(sel_id, held_ids)
    # 8. stop reason
    explain = {
        "search_spec_met": "a design met every criterion on every search condition",
        "model_done": "the model declared that no further structural change would help",
        "model_unavailable": "three model calls in a row failed",
        "stagnation": "the best score stopped improving",
        "time_budget": "the wall-clock budget was used up",
        "proposal_budget": "the maximum number of proposals was reached",
        "round_budget": "the maximum number of rounds was reached",
        "sim_budget": "the simulation budget was used up",
        "smoke": "smoke test (reference and witness only, no model)",
        "incomplete": "the job ended before the search finished (killed, timed out, or still running)",
    }
    s += ["", "## Stop reason", "", f"**{stop_reason}**: {explain.get(stop_reason, '')}.",
          f"Spec met on search conditions: **{met_search}**; on all conditions including held-out: **{met_all}**."]
    # 9. time
    s += ["", "## Time and tokens", ""]
    if timing:
        s.append(_table(["quantity", "value"], [
            ["wall time", f"{timing.get('wall_s', 0):.0f} s"],
            ["model calls", timing.get("model_calls")], ["time in model calls", f"{timing.get('model_s', 0):.0f} s"],
            ["prompt tokens", timing.get("prompt_tokens")], ["completion tokens", timing.get("completion_tokens")],
            ["of which reasoning tokens", timing.get("reasoning_tokens") or "not reported"],
            ["simulations run", timing.get("n_sims")], ["cache hits (not re-simulated)", timing.get("cache_hits")],
            ["simulator time (sum over parallel runs)", f"{timing.get('sim_seconds', 0):.0f} s"],
            ["simulation wall time", f"{timing.get('sim_wall_s', 0):.0f} s"],
            ["screening simulations", timing.get("n_screen_sims", "-")],
            ["screening wall time", f"{timing.get('screen_s', 0):.0f} s"],
            ["value sizing wall time", f"{timing.get('size_s', timing.get('refine_s', 0)):.0f} s"],
            ["designs proposed / invalid / duplicate", f"{timing.get('n_proposals', '-')} / "
             f"{timing.get('n_invalid', '-')} / {timing.get('n_duplicate', '-')}"],
            ["structures / passed the screen", f"{timing.get('n_topologies', '-')} / {timing.get('n_screen_pass', '-')}"]]))
        s += ["", "Value sizing runs while the model is thinking, so model and simulation times overlap."]
    else:
        s.append("Not available (run incomplete).")
    # 10. files
    s += ["", "## Files", "", _table(["file", "contents"], [
        ["selected/circuit.json, selected/<cond>.net", "selected design and its exact netlist for every condition"],
        ["proposals.csv", "every design the model proposed and what happened to it (screen powers)"],
        ["candidates.csv", "every design evaluated (one row per design and condition set)"],
        ["robust.json, reference_screen.json", "Monte Carlo result; the reference's screen powers"],
        ["measurements.csv", "every measurement, per design and condition"],
        ["checks.csv", "every pass/fail decision with margin"],
        ["candidates/<id>/circuit.json", "each design's circuit"],
        ["llm/iter-NN-a.json", "prompts, replies and model reasoning (NN = round)"],
        ["events.jsonl", "timeline of the run"], ["sims/<hash>/", "LTspice netlists, logs and waveforms"],
        ["timing.json, outcome.json, spec.json, config.json", "timing, result, spec and settings"]])]
    text = "\n".join(s) + "\n"
    (out / "report.md").write_text(text, encoding="utf-8")
    summary = {"stop_reason": stop_reason, "met_search": met_search, "met_all": met_all, "selected_id": sel_id,
               "selected_topology": {"name": sel.get("name"), "topo_hash": sel.get("topo_hash")},
               "reference_id": ref_id, "failed_checks": fails, "timing": timing}
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return text


if __name__ == "__main__":
    print(build_report(sys.argv[1] if len(sys.argv) > 1 else "."))
