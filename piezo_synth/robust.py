"""Monte Carlo robustness of a design under component tolerances and controller timing error."""
from __future__ import annotations

import random
from typing import List

from . import spec
from .bench import evaluate_many
from .circuit import Circuit, get_param, numeric_params, with_param


def perturb(c: Circuit, rng: random.Random, tol: dict = None) -> Circuit:
    tol = spec.TOLERANCES if tol is None else tol
    types = {x.id: x.type for x in c.components}
    p = c
    for cid, fld in numeric_params(c):
        v = get_param(p, cid, fld)
        if fld == "phase":
            p = with_param(p, cid, fld, v + rng.uniform(-tol["phase"], tol["phase"]))
        else:
            t = tol["ton"] if fld == "ton" else tol.get(types[cid], 0.0)
            p = with_param(p, cid, fld, v * (1 + rng.uniform(-t, t)))
    return p


def monte_carlo(c: Circuit, conditions, sim, rng: random.Random, n: int, label: str) -> dict:
    samples: List[Circuit] = [perturb(c, rng) for _ in range(n)]
    evs = evaluate_many(samples, conditions, sim, [f"{label}-mc{k:02d}" for k in range(n)])
    per = {cond.id: 0 for cond in conditions}
    for ev in evs:
        for cond in conditions:
            if all(ch.passed for ch in ev.checks if ch.condition == cond.id):
                per[cond.id] += 1
    return {"n": n, "pass_all": sum(ev.all_pass for ev in evs) / n if n else 0.0,
            "per_condition": {k: v / n for k, v in per.items()} if n else {},
            "tolerances": dict(spec.TOLERANCES),
            "worst_condition": min(per, key=per.get) if per else None}
