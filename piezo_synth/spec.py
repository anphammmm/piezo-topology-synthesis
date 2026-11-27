"""The experiment specification: operating conditions, pass/fail criteria, limits, simulation settings.

Search conditions (S*) are shown to the model and used for scoring. Held-out conditions (H*) are
evaluated only on the selected design and the reference, after the search has stopped.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import List


@dataclass(frozen=True)
class Condition:
    id: str
    split: str          # "search" | "heldout"
    label: str
    ip: float           # piezo current amplitude, A peak
    freq: float         # excitation frequency, Hz
    cp: float           # piezo capacitance, F
    rp: float           # piezo leakage resistance, ohm
    rl: float           # load resistance, ohm
    temp: float         # simulation temperature, degC


@dataclass(frozen=True)
class Criterion:
    id: str
    meas: str           # measurement name (see netlist.MEAS_NAMES, plus derived "dv")
    op: str             # ">=" | "<="
    limit: float
    scale: float        # normalises margins: margin = (meas - limit)/scale for ">="
    unit: str
    description: str


RP = 20e6

CONDITIONS: List[Condition] = [
    Condition("S1", "search", "nominal", 50e-6, 100, 25e-9, RP, 330e3, 27),
    Condition("S2", "search", "heavy load", 50e-6, 100, 25e-9, RP, 150e3, 27),
    Condition("S3", "search", "strong excitation, light load", 100e-6, 100, 25e-9, RP, 2.2e6, 27),
    Condition("S4", "search", "weak excitation", 30e-6, 100, 25e-9, RP, 1e6, 27),
    Condition("S5", "search", "low frequency", 40e-6, 80, 25e-9, RP, 470e3, 27),
    Condition("S6", "search", "Cp +20 %, hot", 50e-6, 100, 30e-9, RP, 330e3, 60),
    Condition("H1", "heldout", "weak excitation, mid load", 35e-6, 100, 25e-9, RP, 470e3, 27),
    Condition("H2", "heldout", "high frequency, Cp −15 %", 60e-6, 120, 21.25e-9, RP, 220e3, 27),
    Condition("H3", "heldout", "very strong excitation, open load, cold", 120e-6, 100, 25e-9, RP, 10e6, -20),
    Condition("H4", "heldout", "hot, heavy load", 50e-6, 100, 25e-9, RP, 200e3, 85),
]

CRITERIA: List[Criterion] = [
    Criterion("vout_min", "vavg", ">=", 1.8, 1.8, "V", "settled mean output reaches the load's minimum supply"),
    Criterion("vout_max", "vmax", "<=", 3.6, 3.6, "V", "output never exceeds the load's absolute maximum"),
    Criterion("ripple", "vpp", "<=", 0.05, 0.05, "V", "peak-to-peak ripple in the final window"),
    Criterion("startup", "tup", "<=", 0.4, 0.4, "s", "cold start: first time output reaches 1.8 V"),
    Criterion("settled", "dv", "<=", 0.02, 0.02, "V", "mean output changes little between the last two windows"),
]

LIMITS = {
    "max_components": 16,
    "max_switches": 4,
    "max_sync": 2,
    "R": (1.0, 1e8),
    "C": (1e-10, 47e-6),
    "L": (1e-5, 1e-2),
    "ton": (1e-7, 1e-3),
    "phase": (-0.25, 0.25),
    "l_rser_base": 2.0,
    "l_rser_per_h": 5000.0,
}

SIM = {"tstop": 0.8, "maxstep": 2e-6, "win": (0.7, 0.8), "win_prev": (0.6, 0.7)}

CTRL_SINK_A = 0.5e-6   # supply current charged per SYNC controller, drawn from "out"


def search_conditions() -> List[Condition]:
    return [c for c in CONDITIONS if c.split == "search"]


def heldout_conditions() -> List[Condition]:
    return [c for c in CONDITIONS if c.split == "heldout"]


def condition(cid: str) -> Condition:
    for c in CONDITIONS:
        if c.id == cid:
            return c
    raise KeyError(cid)


def _jsonable(v):
    return list(v) if isinstance(v, tuple) else v


def spec_dict() -> dict:
    return {
        "conditions": [asdict(c) for c in CONDITIONS],
        "criteria": [asdict(c) for c in CRITERIA],
        "limits": {k: _jsonable(v) for k, v in LIMITS.items()},
        "sim": {k: _jsonable(v) for k, v in SIM.items()},
        "ctrl_sink_a": CTRL_SINK_A,
    }
