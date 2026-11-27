"""Value sizing for a fixed topology: an elitist (1+lambda) evolution strategy in log-parameter space.

Each generation is one batch of lambda designs, simulated in parallel. The step size follows a
success rule (grow after an improving generation, shrink otherwise). The sizer is resumable: the
search runs generations while the model is thinking and continues the same sizer on the next wait.
Like simulation-in-loop feasibility sizing, it stops as soon as a design meets the whole spec.
"""
from __future__ import annotations

import math
import random
from typing import List, Optional

from .circuit import Circuit, design_hash, get_param, numeric_params, with_param
from .evaluate import Evaluation, is_better

SIGMA0 = 0.6          # log-space step: one sigma is a factor of ~1.8
SIGMA_MIN = 0.02
GROW, SHRINK = 1.3, 0.82
PHASE_SCALE = 0.1     # phase is additive: one sigma moves it by PHASE_SCALE * sigma periods


class Sizer:
    def __init__(self, circuit: Circuit, start_ev: Evaluation, budget: int, rng: random.Random, lam: int = 8,
                 sigma0: float = SIGMA0):
        self.params = numeric_params(circuit)
        self.best, self.best_ev = circuit, start_ev
        self.ncomp = len(circuit.components)
        self.budget, self.rng, self.lam = budget, rng, max(1, lam)
        self.sigma = sigma0
        self.n_evals = self.generations = 0
        self.seen = {design_hash(circuit)}
        self.done, self.reason = False, ""
        self._check_done()

    def _check_done(self) -> None:
        if self.done:
            return
        if self.best_ev.all_pass:
            self.done, self.reason = True, "spec_met"
        elif not self.params:
            self.done, self.reason = True, "no_parameters"
        elif self.n_evals >= self.budget:
            self.done, self.reason = True, "budget"
        elif self.sigma < SIGMA_MIN:
            self.done, self.reason = True, "converged"

    def _mutate(self) -> Circuit:
        c = self.best
        for cid, fld in self.params:
            v = get_param(c, cid, fld)
            z = self.rng.gauss(0.0, 1.0) * self.sigma
            c = with_param(c, cid, fld, v + PHASE_SCALE * z if fld == "phase" else v * math.exp(z))
        return c

    def ask(self) -> List[Circuit]:
        """The next generation (distinct, never-seen designs). Empty when done."""
        if self.done:
            return []
        n = min(self.lam, self.budget - self.n_evals)
        out, tries = [], 0
        while len(out) < n and tries < 50 * n:
            tries += 1
            c = self._mutate()
            h = design_hash(c)
            if h not in self.seen:
                self.seen.add(h)
                out.append(c)
        if not out:                      # every mutation clamps onto known designs: nothing left to try
            self.done, self.reason = True, "converged"
        return out

    def tell(self, circuits: List[Circuit], evs: List[Evaluation]) -> Optional[Circuit]:
        """Record a generation's evaluations; returns the new best circuit if it improved."""
        self.n_evals += len(circuits)
        self.generations += 1
        improved = None
        for c, ev in zip(circuits, evs):
            if is_better(ev, self.best_ev, self.ncomp, self.ncomp):
                self.best, self.best_ev, improved = c, ev, c
        self.sigma *= GROW if improved is not None else SHRINK
        self._check_done()
        return improved
