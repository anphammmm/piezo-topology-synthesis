"""LTspice netlist for one circuit under one operating condition, plus the reference and witness circuits.

The harness owns everything except the proposed components: the piezo model, the load, controller
supply sinks, 1 GOhm bleed resistors on internal nodes and the piezo terminals (to avoid floating-node errors), device
models, the 0.8 s cold-start transient and the measurements.
"""
from __future__ import annotations

from typing import Tuple

from .circuit import Circuit, Component, canonical
from . import spec
from .spec import CTRL_SINK_A, LIMITS, SCREEN, SIM, Condition

MODELS_TEXT = """.model DSCH D(Is=5e-8 Rs=1 N=1.05 Cjo=10p BV=30 IBV=1u EG=0.69 XTI=2)
.model DSI D(Is=2.5n Rs=0.6 N=1.75 Cjo=4p BV=75 IBV=1u)
.model DZ33 D(Is=1e-12 Rs=5 N=1.5 BV=3.3 IBV=1u)
.model SWI SW(Ron=2 Roff=1G Vt=0.5 Vh=0)"""

MEAS_NAMES = ("vavg", "vavg_prev", "vpp", "vmax", "tup", "pload", "pext")
SCREEN_MEAS_NAMES = ("isn", "vout")


def fmt(v: float) -> str:
    return "%.6g" % v


def sync_timing(ton: float, phase: float, edges: str, freq: float) -> Tuple[float, float]:
    """(t0, period) of the controller's pulses. The piezo current is Ip*sin(2*pi*f*t), so the
    open-circuit piezo voltage peaks positive at t = 1/(2f) + k/f and negative at t = k/f.
    phase shifts the pulses by that fraction of the excitation period."""
    shift = (phase or 0.0) / freq
    if edges == "pos":
        period = 1.0 / freq
        t0 = (0.5 / freq + shift) % period
    elif edges == "neg":
        period = 1.0 / freq
        t0 = shift % period
    else:
        period = 0.5 / freq
        t0 = shift % period
    if abs(t0 - period) < 1e-15 or abs(t0) < 1e-15:
        t0 = 0.0
    return t0, period


def _component_line(x: Component) -> str:
    a, b = x.nodes if x.nodes else ("", "")
    if x.type in ("R", "C"):
        return f"{x.id} {a} {b} {fmt(x.value)}"
    if x.type == "L":
        rser = LIMITS["l_rser_base"] + LIMITS["l_rser_per_h"] * x.value
        return f"{x.id} {a} {b} {fmt(x.value)} Rser={fmt(rser)}"
    if x.type == "D":
        return f"{x.id} {a} {b} {x.model}"
    if x.type == "S":
        return f"{x.id} {a} {b} {x.ctrl}_g 0 SWI"
    raise ValueError(x.type)


def _bench(cc: Circuit, cond: Condition, title: str, load_lines) -> list:
    """Piezo, load lines, controller sinks, proposed components, pulse sources, bleeds, models, .temp."""
    lines = [f"* {title or cc.name} | condition {cond.id}",
             f"Ipz pzn pzp SINE(0 {fmt(cond.ip)} {fmt(cond.freq)})",
             f"Cpz pzp pzn {fmt(cond.cp)}",
             f"Rpz pzp pzn {fmt(cond.rp)}",
             *load_lines]
    syncs = [x for x in cc.components if x.type == "SYNC"]
    for k, _ in enumerate(syncs, 1):
        lines.append(f"Ictl{k} out 0 {fmt(CTRL_SINK_A)}")
    for x in cc.components:
        if x.type != "SYNC":
            lines.append(_component_line(x))
    for x in syncs:
        t0, period = sync_timing(x.ton, x.phase, x.edges or "both", cond.freq)
        lines.append(f"V{x.id} {x.id}_g 0 PULSE(0 1 {fmt(t0)} 100n 100n {fmt(x.ton)} {fmt(period)})")
    # bleed resistors: internal nodes, and the piezo terminals (a design may couple them only through capacitors)
    internal = ["pzp", "pzn"] + sorted({n for x in cc.components for n in x.nodes} - {"0", "pzp", "pzn", "out"})
    for n in internal:
        lines.append(f"Rbleed_{n} {n} 0 1G")
    lines.append(MODELS_TEXT)
    lines.append(f".temp {fmt(cond.temp)}")
    return lines


def build_screen_netlist(c: Circuit, cond: Condition, title: str = "") -> str:
    """Short run with out held at SCREEN['vstore'] behind a sense resistor (see spec.SCREEN)."""
    cc = canonical(c)
    vst, rs = SCREEN["vstore"], SCREEN["rsense"]
    tstop = SCREEN["cycles"] / cond.freq
    w0 = tstop - SCREEN["avg_cycles"] / cond.freq
    lines = _bench(cc, cond, title, [f"Rsense out vsn {fmt(rs)}", f"Vst vsn 0 {fmt(vst)}"])
    lines += [f".tran 0 {fmt(tstop)} 0 {fmt(SIM['maxstep'])}",
              ".save V(out) V(vsn)",
              f".meas TRAN isn AVG V(out,vsn) FROM={fmt(w0)} TO={fmt(tstop)}",
              f".meas TRAN vout AVG V(out) FROM={fmt(w0)} TO={fmt(tstop)}",
              ".end"]
    return "\n".join(lines) + "\n"


def build_netlist(c: Circuit, cond: Condition, title: str = "", save_all: bool = False) -> str:
    cc = canonical(c)
    w0, w1 = SIM["win"]
    p0, p1 = SIM["win_prev"]
    tstop = SIM["tstop"]
    lines = _bench(cc, cond, title, [f"RL out 0 {fmt(cond.rl)}"])
    lines.append(f".tran 0 {fmt(tstop)} 0 {fmt(SIM['maxstep'])}")
    if not save_all:
        lines.append(".save V(out) V(pzp) V(pzn) I(Ipz)")
    lines += [
        f".meas TRAN vavg AVG V(out) FROM={fmt(w0)} TO={fmt(w1)}",
        f".meas TRAN vavg_prev AVG V(out) FROM={fmt(p0)} TO={fmt(p1)}",
        f".meas TRAN vpp PP V(out) FROM={fmt(w0)} TO={fmt(w1)}",
        f".meas TRAN vmax MAX V(out) FROM=0 TO={fmt(tstop)}",
        f".meas TRAN tup FIND time WHEN V(out)={fmt(spec.vmin())} RISE=1",
        f".meas TRAN pload AVG V(out)*V(out)/{fmt(cond.rl)} FROM={fmt(w0)} TO={fmt(w1)}",
        f".meas TRAN pext AVG V(pzp,pzn)*I(Ipz) FROM={fmt(w0)} TO={fmt(w1)}",
        ".end",
    ]
    return "\n".join(lines) + "\n"


def _bridge() -> list:
    return [Component("D1", "D", ("pzp", "out"), model="DSCH"),
            Component("D2", "D", ("pzn", "out"), model="DSCH"),
            Component("D3", "D", ("0", "pzp"), model="DSCH"),
            Component("D4", "D", ("0", "pzn"), model="DSCH"),
            Component("C1", "C", ("out", "0"), value=2.2e-6)]


def reference_circuit() -> Circuit:
    """Full-bridge rectifier with a 2.2 uF storage capacitor: the standard passive interface."""
    return Circuit(name="FBR reference (4x Schottky, 2.2 uF)", components=_bridge(),
                   rationale="standard full-bridge rectifier")


def witness_circuit() -> Circuit:
    """Parallel SSHI + bridge + 3.3 V zener clamp. Used only by the smoke test to show the spec is
    reachable in principle; never shown to the model."""
    comps = _bridge() + [
        Component("L1", "L", ("pzp", "n1"), value=4.7e-3),
        Component("S1", "S", ("n1", "pzn"), ctrl="G1"),
        Component("G1", "SYNC", (), ton=34e-6, phase=0.0, edges="both"),
        Component("D5", "D", ("0", "out"), model="DZ33"),
    ]
    return Circuit(name="witness: p-SSHI + bridge + zener clamp", components=comps)


def _stacked_clamp_witness() -> Circuit:
    """P2: parallel SSHI + bridge, clamped near 5 V by the 3.3 V zener in series with three silicon diodes."""
    comps = _bridge() + [
        Component("L1", "L", ("pzp", "n1"), value=4.7e-3),
        Component("S1", "S", ("n1", "pzn"), ctrl="G1"),
        Component("G1", "SYNC", (), ton=34e-6, phase=0.0, edges="both"),
        Component("D5", "D", ("z1", "out"), model="DZ33"),
        Component("D6", "D", ("z1", "z2"), model="DSI"),
        Component("D7", "D", ("z2", "z3"), model="DSI"),
        Component("D8", "D", ("z3", "0"), model="DSI"),
    ]
    return Circuit(name="witness: p-SSHI + bridge + stacked clamp (3.3 V zener + 3 diodes)", components=comps)


def _multiplier_witness() -> Circuit:
    """P3: passive two-stage Cockcroft-Walton multiplier (no controller to supply) with a 3.3 V clamp."""
    comps = [
        Component("R1", "R", ("pzn", "0"), value=1.0),
        Component("C1", "C", ("pzp", "n1"), value=1e-6),
        Component("D1", "D", ("0", "n1"), model="DSCH"),
        Component("D2", "D", ("n1", "n2"), model="DSCH"),
        Component("C2", "C", ("n2", "0"), value=1e-6),
        Component("C3", "C", ("n1", "n3"), value=1e-6),
        Component("D3", "D", ("n2", "n3"), model="DSCH"),
        Component("D4", "D", ("n3", "out"), model="DSCH"),
        Component("C4", "C", ("out", "n2"), value=1e-6),
        Component("C5", "C", ("out", "0"), value=0.47e-6),
        Component("D5", "D", ("0", "out"), model="DZ33"),
    ]
    return Circuit(name="witness: 2-stage Cockcroft-Walton multiplier + zener clamp", components=comps)


def spec_witness() -> Circuit:
    """A hand-made circuit meant to meet the active specification (feasibility evidence; never shown to the
    model). For specs without a dedicated one, the P1 witness."""
    return {"P2": _stacked_clamp_witness, "P3": _multiplier_witness}.get(spec.ACTIVE, witness_circuit)()
