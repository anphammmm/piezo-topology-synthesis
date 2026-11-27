"""Evaluate circuits on a set of conditions: build the netlists, simulate them in one parallel batch."""
from __future__ import annotations

from typing import List

from .circuit import Circuit
from .evaluate import Evaluation, evaluate
from .netlist import build_netlist


def evaluate_many(circuits: List[Circuit], conditions, sim, labels: List[str]) -> List[Evaluation]:
    """All circuits x conditions go to the simulator as one batch, so they run in parallel."""
    jobs = [(f"{lab}/{cond.id}", build_netlist(c, cond, title=lab))
            for c, lab in zip(circuits, labels) for cond in conditions]
    results = sim.run(jobs) if jobs else []
    n = len(conditions)
    return [evaluate({cond.id: r for cond, r in zip(conditions, results[k * n:(k + 1) * n])}, conditions)
            for k in range(len(circuits))]


def evaluate_circuit(c: Circuit, conditions, sim, label: str) -> Evaluation:
    return evaluate_many([c], conditions, sim, [label])[0]
