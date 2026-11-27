"""Fast screen of an untuned topology: net power into a storage node held at 1.8 V (see spec.SCREEN).

A few value presets are tried (the proposed values, LC-resonance switch timings, random spreads) on
the screen conditions with short simulations; the best preset is kept as the starting point for
sizing. The screen is a necessary condition for vout_min, relaxed by alpha because values are untuned.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import spec
from .circuit import Circuit, design_hash, get_param, numeric_params, with_param
from .netlist import build_screen_netlist


def p_fbr_ideal(cond: spec.Condition) -> float:
    """Maximum power of an ideal (lossless-diode) full-bridge rectifier: f*Cp*Voc^2 = Ip^2/(4 pi^2 f Cp)."""
    return cond.ip ** 2 / (4 * math.pi ** 2 * cond.freq * cond.cp)


def p_required(cond: spec.Condition) -> float:
    return spec.SCREEN["vstore"] ** 2 / cond.rl


@dataclass
class ScreenResult:
    passed: bool
    circuit: Circuit                      # best preset
    worst_ratio: float                    # min over screen conditions of p_net / p_required
    ratio: Dict[str, float] = field(default_factory=dict)
    p_net: Dict[str, Optional[float]] = field(default_factory=dict)
    p_req: Dict[str, float] = field(default_factory=dict)
    gain: Dict[str, Optional[float]] = field(default_factory=dict)   # p_net / ideal-FBR maximum
    n_presets: int = 0
    n_sims: int = 0
    sim_failed: bool = False
    error: str = ""

    def summary(self) -> str:
        parts = []
        for cid in sorted(self.ratio):
            pn = self.p_net.get(cid)
            got = "simulation failed" if pn is None else f"{pn * 1e6:.3g} uW"
            parts.append(f"{cid}: {got} of {self.p_req[cid] * 1e6:.3g} uW needed ({self.ratio[cid] * 100:.0f} %)")
        return "; ".join(parts)


def physics_presets(c: Circuit) -> List[Circuit]:
    """Switch on-times from the LC resonance with the nominal piezo capacitance: a full inversion
    (pi*sqrt(L*Cp)) and a quarter period (charge extraction). Empty if there is no SYNC or no inductor."""
    syncs = [x for x in c.components if x.type == "SYNC"]
    inds = sorted((x for x in c.components if x.type == "L"), key=lambda x: x.id)
    if not syncs or not inds:
        return []
    cp = spec.search_conditions()[0].cp
    res = math.pi * math.sqrt(inds[0].value * cp)
    out = []
    for ton in (res, res / 2):
        p = c
        for s in syncs:
            p = with_param(p, s.id, "ton", ton)
        out.append(p)
    return out


def random_preset(c: Circuit, rng: random.Random, spread: float) -> Circuit:
    p = c
    for cid, fld in numeric_params(c):
        v = get_param(p, cid, fld)
        if fld == "phase":
            p = with_param(p, cid, fld, v + rng.uniform(-0.1, 0.1))
        else:
            p = with_param(p, cid, fld, v * math.exp(rng.uniform(-math.log(spread), math.log(spread))))
    return p


def presets(c: Circuit, n: int, rng: random.Random, spread: float) -> List[Circuit]:
    out, seen = [], set()
    for p in [c, *physics_presets(c)]:
        if design_hash(p) not in seen and len(out) < max(1, n):
            seen.add(design_hash(p))
            out.append(p)
    tries = 0
    while len(out) < n and numeric_params(c) and tries < 10 * n:
        tries += 1
        p = random_preset(c, rng, spread)
        if design_hash(p) not in seen:
            seen.add(design_hash(p))
            out.append(p)
    return out


def screen(c: Circuit, sim, rng: random.Random, label: str, conditions=None, n_presets: Optional[int] = None,
           alpha: Optional[float] = None) -> ScreenResult:
    conds = [spec.condition(cid) for cid in (conditions or spec.SCREEN["conditions"])]
    alpha = spec.SCREEN["alpha"] if alpha is None else alpha
    ps = presets(c, n_presets or spec.SCREEN["presets"], rng, spec.SCREEN["spread"])
    jobs = [(f"{label}-screen{k}/{cond.id}", build_screen_netlist(p, cond, title=f"{label}-screen{k}"))
            for k, p in enumerate(ps) for cond in conds]
    results = sim.run(jobs)
    k_res = len(conds)
    best: Optional[ScreenResult] = None
    any_ok = False
    errors = []
    for k, p in enumerate(ps):
        ratio, p_net, p_req, gain = {}, {}, {}, {}
        for j, cond in enumerate(conds):
            r = results[k * k_res + j]
            p_req[cond.id] = p_required(cond)
            isn = r.meas.get("isn") if r.ok else None
            try:
                isn = float(isn)
            except (TypeError, ValueError):
                isn = None
            if isn is None or not math.isfinite(isn):
                errors.append(r.error or "no isn measurement")
                p_net[cond.id], gain[cond.id], ratio[cond.id] = None, None, -math.inf
                continue
            any_ok = True
            pn = spec.SCREEN["vstore"] * isn / spec.SCREEN["rsense"]
            p_net[cond.id] = pn
            gain[cond.id] = pn / p_fbr_ideal(cond)
            ratio[cond.id] = pn / p_req[cond.id]
        worst = min(ratio.values())
        cand = ScreenResult(worst >= alpha, p, worst, ratio, p_net, p_req, gain)
        if best is None or worst > best.worst_ratio:
            best = cand
    best.n_presets, best.n_sims = len(ps), len(jobs)
    best.sim_failed = not any_ok
    if best.sim_failed:
        best.error = " ".join((errors[0] if errors else "simulation failed").split())[:200]
    return best
