"""Physical interpretation of results for the model: turns measurements and screen powers into short
statements about what is wrong (no output, too little power, overvoltage, slow start, ...).

The statements name the symptom and the part of the circuit's job that fails, not a specific fix, so
the feedback does not steer the model toward a known topology.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from . import spec
from .evaluate import Evaluation

_LIM = {c.id: c.limit for c in spec.CRITERIA}
VMIN, VMAX = _LIM["vout_min"], _LIM["vout_max"]
DEAD_V = 0.5 * VMIN
MAJOR = ("pinned", "sim_failed", "underpower", "overvoltage")   # codes tracked for repeated failures


@dataclass(frozen=True)
class Hint:
    code: str
    text: str


def _label(cid: str) -> str:
    try:
        return f"{cid} ({spec.condition(cid).label})"
    except KeyError:
        return cid


def _list(items: Iterable[str], n: int = 3) -> str:
    items = list(items)
    return ", ".join(items[:n]) + (f" and {len(items) - n} more" if len(items) > n else "")


def hints(ev: Optional[Evaluation] = None, screen=None) -> List[Hint]:
    out: List[Hint] = []
    if ev is not None:
        failed = [k for k, ok in ev.sim_ok.items() if not ok]
        if failed:
            err = " ".join(ev.sim_error.get(failed[0], "").split())[:160]
            out.append(Hint("sim_failed", f"the simulation failed on {_list(failed)} ({err}); the circuit may "
                                          f"have a short, a loop of ideal sources/switches, or a floating section"))
        ok = {k: m for k, m in ev.meas.items() if ev.sim_ok.get(k)}
        vmax = {k: m.get("vmax") for k, m in ok.items() if m.get("vmax") is not None}
        if ok and vmax and max(vmax.values()) < DEAD_V:
            out.append(Hint("pinned", f"V(out) never exceeds {max(vmax.values()):.2g} V on any condition: no "
                                      f"charge reaches the storage, or something conducts from out to ground "
                                      f"(check every diode's orientation: nodes are [anode, cathode])"))
        else:
            low = [(k, m["vavg"]) for k, m in ok.items() if m.get("vavg") is not None and m["vavg"] < VMIN
                   and (m.get("vmax") or 0) <= VMAX]
            if low:
                out.append(Hint("underpower", "the output settles below 1.8 V on " +
                                _list(f"{_label(k)} at {v:.2f} V" for k, v in low) +
                                ": the interface does not deliver enough power there"))
            high = [(k, v) for k, v in vmax.items() if v > VMAX]
            if high:
                out.append(Hint("overvoltage", "V(out) exceeds 3.6 V on " +
                                _list(f"{_label(k)} (peak {v:.2f} V)" for k, v in high) +
                                ": the output needs limiting when the source is strong or the load light"))
            slow = [(k, m.get("tup")) for k, m in ok.items() if (m.get("vavg") or 0) >= VMIN
                    and (m.get("tup") is None or m["tup"] > _LIM["startup"])]
            if slow:
                out.append(Hint("slow_start", "start-up is too slow on " +
                                _list(f"{k} ({'never' if t is None else f'{t:.2f} s'})" for k, t in slow) +
                                ": the storage charges too slowly from 0 V (too much capacitance or too "
                                "little power at low voltage)"))
            drift = [(k, m.get("dv")) for k, m in ok.items() if (m.get("vavg") or 0) >= VMIN
                     and m.get("dv") is not None and m["dv"] > _LIM["settled"]]
            if drift:
                out.append(Hint("not_settled", "the output is still drifting at 0.8 s on " +
                                _list(f"{k} ({d * 1e3:.0f} mV between windows)" for k, d in drift) +
                                ": the storage time constant is too long"))
            rip = [(k, m.get("vpp")) for k, m in ok.items() if m.get("vpp") is not None and m["vpp"] > _LIM["ripple"]]
            if rip:
                out.append(Hint("ripple", "ripple is too large on " +
                                _list(f"{k} ({v * 1e3:.0f} mV)" for k, v in rip) +
                                ": the storage cannot buffer the charge pulses against the load"))
    if screen is not None:
        if screen.sim_failed:
            out.append(Hint("sim_failed", f"the screening simulation failed ({screen.error})"))
        else:
            short = [(k, r) for k, r in screen.ratio.items() if r < 1.0]
            if short and not any(h.code == "underpower" for h in out):
                out.append(Hint("underpower", "with the output fixed at 1.8 V, the net power delivered covers only " +
                                _list(f"{r * 100:.0f} % of the load's need on {_label(k)}" for k, r in short) +
                                " (best of the value presets tried)"))
    return out


def codes(hs: List[Hint]) -> set:
    return {h.code for h in hs}


def repeated(history: List[set], n: int = 3) -> List[str]:
    """Major problem codes shared by the last n results (empty if fewer than n)."""
    if len(history) < n:
        return []
    common = set.intersection(*[set(h) for h in history[-n:]])
    return [c for c in MAJOR if c in common]


def hint_text(hs: List[Hint]) -> str:
    return "\n".join(f"- {h.text}" for h in hs)
