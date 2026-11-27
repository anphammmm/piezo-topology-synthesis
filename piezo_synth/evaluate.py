"""Turn simulation measurements into pass/fail checks against the spec, and a scalar score."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .spec import CRITERIA, Condition, Criterion


@dataclass
class Check:
    condition: str
    criterion: str
    measured: Optional[float]
    limit: float
    op: str
    margin: float
    passed: bool


@dataclass
class Evaluation:
    checks: List[Check] = field(default_factory=list)
    meas: Dict[str, dict] = field(default_factory=dict)
    sim_ok: Dict[str, bool] = field(default_factory=dict)
    sim_error: Dict[str, str] = field(default_factory=dict)
    scalar: float = 0.0
    cond_pass: int = 0
    checks_pass: int = 0
    all_pass: bool = False


def _num(v) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _clip(v: float, lo: float, hi: float) -> float:
    return min(max(v, lo), hi)


def evaluate(results: dict, conditions: List[Condition], criteria: List[Criterion] = CRITERIA) -> Evaluation:
    """results: condition id -> SimResult. Missing results count as failed simulations."""
    ev = Evaluation()
    for cond in conditions:
        r = results.get(cond.id)
        ok = bool(r is not None and r.ok)
        ev.sim_ok[cond.id] = ok
        if not ok:
            ev.sim_error[cond.id] = (r.error if r is not None else "not simulated") or "simulation failed"
        meas = {k: _num(v) for k, v in (r.meas.items() if ok else [])}
        if meas.get("vavg") is not None and meas.get("vavg_prev") is not None:
            meas["dv"] = abs(meas["vavg"] - meas["vavg_prev"])
        ev.meas[cond.id] = meas
        all_ok = True
        for crit in criteria:
            m = meas.get(crit.meas)
            if m is None:
                margin = -1.0
            elif crit.op == ">=":
                margin = (m - crit.limit) / crit.scale
            else:
                margin = (crit.limit - m) / crit.scale
            passed = m is not None and margin >= 0
            all_ok = all_ok and passed
            ev.checks.append(Check(cond.id, crit.id, m, crit.limit, crit.op, margin, passed))
        ev.cond_pass += int(all_ok)
    ev.checks_pass = sum(c.passed for c in ev.checks)
    ev.all_pass = bool(ev.checks) and ev.checks_pass == len(ev.checks)
    ev.scalar = (10 * ev.cond_pass + ev.checks_pass
                 + sum(_clip(c.margin, -1, 0) for c in ev.checks)
                 + 0.05 * sum(_clip(c.margin, 0, 0.5) for c in ev.checks))
    return ev


_UNITS = {c.id: c.unit for c in CRITERIA}


def diagnose(ev: Evaluation, limit: int = 8) -> str:
    """Failing checks, worst first, then simulation failures. Empty string if everything passed."""
    failed_sim = {k for k, ok in ev.sim_ok.items() if not ok}
    bad = sorted((c for c in ev.checks if not c.passed and c.condition not in failed_sim),
                 key=lambda c: c.margin)
    lines = []
    for c in bad[:limit]:
        u = _UNITS.get(c.criterion, "")
        got = "not reached / not measured" if c.measured is None else f"{c.measured:.4g} {u}"
        lines.append(f"{c.condition} {c.criterion}: {got} (needs {c.op} {c.limit:g} {u}, margin {c.margin:+.2f})")
    if len(bad) > limit:
        lines.append(f"... and {len(bad) - limit} more failing checks")
    for k in sorted(failed_sim):
        err = " ".join(ev.sim_error.get(k, "").split())[:200]
        lines.append(f"{k}: simulation failed: {err}")
    return "\n".join(lines)


def is_better(a: Evaluation, b: Optional[Evaluation], ncomp_a: int, ncomp_b: int) -> bool:
    """Higher scalar wins; on a tie, fewer components."""
    if b is None:
        return True
    if a.scalar > b.scalar + 1e-9:
        return True
    if abs(a.scalar - b.scalar) <= 1e-9:
        return ncomp_a < ncomp_b
    return False
