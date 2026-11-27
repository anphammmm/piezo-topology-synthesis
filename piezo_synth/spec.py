"""The experiment specification: operating conditions, pass/fail criteria, limits, simulation settings.

Search conditions (S*) are shown to the model and used for scoring. Held-out conditions (H*) are
evaluated only on the selected design and the reference, after the search has stopped.
"""
from __future__ import annotations

from contextlib import contextmanager
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

_P1_CONDITIONS: List[Condition] = [
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

_P1_CRITERIA: List[Criterion] = [
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

# Fast screen (before any value tuning): the storage node is held at vstore by a source behind a
# sense resistor, and the net power delivered into it is averaged over the last avg_cycles of a
# short run. A design whose net power at 1.8 V is below the load's demand V^2/RL on some condition
# cannot hold vout >= 1.8 V there whatever its storage capacitor; alpha < 1 relaxes the test because
# the values are not tuned yet (the same idea as a relaxed DC-gain filter for unsized amplifiers).
# Robustness check of the selected design (after the search): each Monte Carlo sample draws every
# value uniformly within +/- these relative tolerances (phase: absolute, in periods, standing for
# controller timing error), and is evaluated on all conditions.
TOLERANCES = {"R": 0.05, "C": 0.2, "L": 0.1, "ton": 0.05, "phase": 0.02}

SCREEN = {"vstore": 1.8, "rsense": 100.0, "cycles": 10, "avg_cycles": 4, "alpha": 0.5,
          "conditions": ("S2", "S4", "S6"), "presets": 4, "spread": 3.0}


def _criteria(vmin: float, vmax: float, ripple: float = 0.05, startup: float = 0.4,
              settled: float = 0.02) -> List[Criterion]:
    return [
        Criterion("vout_min", "vavg", ">=", vmin, vmin, "V", "settled mean output reaches the load's minimum supply"),
        Criterion("vout_max", "vmax", "<=", vmax, vmax, "V", "output never exceeds the load's absolute maximum"),
        Criterion("ripple", "vpp", "<=", ripple, ripple, "V", "peak-to-peak ripple in the final window"),
        Criterion("startup", "tup", "<=", startup, startup, "s",
                  f"cold start: first time output reaches {vmin:g} V"),
        Criterion("settled", "dv", "<=", settled, settled, "V",
                  "mean output changes little between the last two windows"),
    ]


def _c(cid, label, ip_ua, freq, cp_nf, rl, temp=27.0):
    return Condition(cid, "search" if cid.startswith("S") else "heldout", label, ip_ua * 1e-6, freq, cp_nf * 1e-9,
                     RP, rl, temp)


@dataclass(frozen=True)
class Spec:
    name: str
    title: str
    hardness: str            # what makes it hard; for the paper and the report, never shown to the model
    conditions: List[Condition]
    criteria: List[Criterion]


SPECS = {
    "P1": Spec("P1", "Sensor supply 1.8-3.6 V", "the full bridge lacks power at weak excitation and heavy load, "
               "and overcharges at strong excitation", _P1_CONDITIONS, _P1_CRITERIA),
    # A 4.5-5.5 V rail: on most conditions the open-circuit voltage is below the window plus two diode drops,
    # so a bridge alone never conducts; strong excitation exceeds 5.5 V, and the only zener breaks at 3.3 V.
    "P2": Spec("P2", "High-voltage rail 4.5-5.5 V", "open-circuit voltage below the output window on most "
               "conditions; the clamp must be composed (the only zener is 3.3 V)", [
        _c("S1", "nominal", 60, 100, 25, 2.2e6),
        _c("S2", "heavy load", 60, 100, 25, 1e6),
        _c("S3", "strong excitation, light load", 120, 100, 25, 10e6),
        _c("S4", "weak excitation", 40, 100, 25, 4.7e6),
        _c("S5", "low frequency", 50, 80, 25, 3.3e6),
        _c("S6", "Cp +20 %, hot", 60, 100, 30, 2.2e6, 60),
        _c("H1", "weak excitation, mid load", 45, 100, 25, 3.3e6),
        _c("H2", "high frequency, Cp -15 %", 70, 120, 21.25, 1.5e6),
        _c("H3", "very strong excitation, open load, cold", 140, 100, 25, 22e6, -20),
        _c("H4", "hot, heavy load", 60, 100, 25, 1.5e6, 85),
    ], _criteria(4.5, 5.5)),
    # Very weak excitation: the open-circuit voltage is below half of 1.8 V, and one synchronous controller's
    # supply current costs more power than the load needs, so the switched interfaces of P1 lose energy.
    "P3": Spec("P3", "Very weak excitation, 1.8-3.6 V", "open-circuit voltage below half the minimum output; a "
               "synchronous controller costs more than the load", [
        _c("S1", "nominal (weak)", 12, 100, 25, 10e6),
        _c("S2", "heavy load", 12, 100, 25, 6.8e6),
        _c("S3", "strong excitation, light load", 40, 100, 25, 22e6),
        _c("S4", "weakest excitation", 8, 100, 25, 22e6),
        _c("S5", "low frequency", 10, 80, 25, 10e6),
        _c("S6", "Cp +20 %, hot", 12, 100, 30, 10e6, 60),
        _c("H1", "weak, mid load", 10, 100, 25, 15e6),
        _c("H2", "high frequency, Cp -15 %", 15, 120, 21.25, 6.8e6),
        _c("H3", "strong excitation, open load, cold", 50, 100, 25, 100e6, -20),
        _c("H4", "warm, heavy load", 12, 100, 25, 6.8e6, 70),
    ], _criteria(1.8, 3.6)),
    # Wide band: 50-200 Hz with the source current proportional to frequency, Cp 17.5-32.5 nF, and the hot,
    # heavy-load corner that P1 kept for the held-out set is now a search condition.
    "P4": Spec("P4", "Wide band 50-200 Hz, Cp +/-30 %", "timing and resonance must hold over a 4x frequency "
               "and 1.9x capacitance range, including 85 C at heavy load", [
        _c("S1", "nominal", 50, 100, 25, 330e3),
        _c("S2", "low frequency, mid load", 25, 50, 25, 680e3),
        _c("S3", "high frequency, small Cp, light load", 100, 200, 17.5, 4.7e6),
        _c("S4", "low frequency, large Cp", 25, 50, 32.5, 1e6),
        _c("S5", "high frequency, large Cp, heavy load", 100, 200, 32.5, 150e3),
        _c("S6", "hot, heavy load", 50, 100, 25, 200e3, 85),
        _c("H1", "75 Hz, Cp +12 %", 37.5, 75, 28, 470e3),
        _c("H2", "150 Hz, Cp -20 %", 75, 150, 20, 220e3),
        _c("H3", "200 Hz, strong, open load, cold", 120, 200, 17.5, 10e6, -20),
        _c("H4", "60 Hz, Cp +20 %, warm", 30, 60, 30, 470e3, 70),
    ], _criteria(1.8, 3.6)),
    # P1's conditions with a tight supply: small ripple needs a large storage capacitance, a fast start a
    # small one.
    "P5": Spec("P5", "Fast start, low ripple, 1.8-3.6 V", "ripple <= 20 mV needs storage capacitance that a "
               "start within 0.15 s cannot charge", list(_P1_CONDITIONS),
               _criteria(1.8, 3.6, ripple=0.02, startup=0.15, settled=0.01)),
}

ACTIVE = "P1"
CONDITIONS: List[Condition] = list(_P1_CONDITIONS)
CRITERIA: List[Criterion] = list(_P1_CRITERIA)


def use(name: str) -> None:
    """Make `name` the active specification. The module-level lists and SCREEN are changed in place, so
    modules that imported them see the new spec."""
    global ACTIVE
    sp = SPECS[name]
    CONDITIONS[:] = sp.conditions
    CRITERIA[:] = sp.criteria
    SCREEN["vstore"] = vmin()
    ACTIVE = name


@contextmanager
def using(name: str):
    prev = ACTIVE
    use(name)
    try:
        yield SPECS[name]
    finally:
        use(prev)


def _limit(cid: str) -> float:
    return next(c.limit for c in CRITERIA if c.id == cid)


def vmin() -> float:
    return _limit("vout_min")


def vmax() -> float:
    return _limit("vout_max")


def limit(cid: str) -> float:
    return _limit(cid)


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
        "name": ACTIVE,
        "title": SPECS[ACTIVE].title,
        "conditions": [asdict(c) for c in CONDITIONS],
        "criteria": [asdict(c) for c in CRITERIA],
        "limits": {k: _jsonable(v) for k, v in LIMITS.items()},
        "sim": {k: _jsonable(v) for k, v in SIM.items()},
        "ctrl_sink_a": CTRL_SINK_A,
        "screen": {k: _jsonable(v) for k, v in SCREEN.items()},
        "tolerances": dict(TOLERANCES),
    }
