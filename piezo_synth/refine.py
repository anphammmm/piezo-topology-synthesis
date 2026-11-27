"""Value tuning for a fixed topology: coordinate search, multiplicative for R/C/L/ton, additive for phase."""
from __future__ import annotations

import random
from typing import Callable, List, Tuple

from .circuit import Circuit, get_param, numeric_params, with_param
from .evaluate import Evaluation, is_better

MIN_FACTOR = 1.05
MIN_ADD = 0.005


def _initial_step(fld: str) -> float:
    if fld == "phase":
        return 0.05
    if fld == "ton":
        return 1.3
    return 2.0


def refine(circuit: Circuit, start: Evaluation, evaluate_fn: Callable[[Circuit], Evaluation], budget: int,
           rng: random.Random, should_stop: Callable[[], bool] = lambda: False
           ) -> Tuple[Circuit, Evaluation, List[Tuple[Circuit, Evaluation]]]:
    """Return (best circuit, its evaluation, every (circuit, evaluation) tried)."""
    params = numeric_params(circuit)
    tried: List[Tuple[Circuit, Evaluation]] = []
    if not params or budget <= 0:
        return circuit, start, tried
    ncomp = len(circuit.components)
    step = {p: _initial_step(p[1]) for p in params}
    best, best_ev = circuit, start
    seen = set()

    def small(p) -> bool:
        return step[p] < (MIN_ADD if p[1] == "phase" else MIN_FACTOR)

    while len(tried) < budget and not all(small(p) for p in params):
        improved = False
        order = list(params)
        rng.shuffle(order)
        for p in order:
            if small(p):
                continue
            cid, fld = p
            cur = get_param(best, cid, fld)
            if fld == "phase":
                cands = [cur + step[p], cur - step[p]]
            else:
                cands = [cur * step[p], cur / step[p]]
            for v in cands:
                if len(tried) >= budget or should_stop():
                    return best, best_ev, tried
                cand = with_param(best, cid, fld, v)
                newv = get_param(cand, cid, fld)
                key = (p, round(newv, 15), id(best))
                if abs(newv - cur) <= 1e-15 * max(1.0, abs(cur)) or key in seen:
                    continue   # clamped at a bound, or already tried from this point
                seen.add(key)
                ev = evaluate_fn(cand)
                tried.append((cand, ev))
                if is_better(ev, best_ev, ncomp, ncomp):
                    best, best_ev = cand, ev
                    improved = True
                    break
        if not improved:
            for p in params:
                step[p] = step[p] / 2 if p[1] == "phase" else step[p] ** 0.5
    return best, best_ev, tried
