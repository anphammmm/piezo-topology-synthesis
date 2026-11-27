"""Prompts for the model. Rebuilt from the search state every iteration (no growing chat history).

Only search conditions appear here: the held-out conditions are never shown to the model.
"""
from __future__ import annotations

import json
import math
from typing import List, Optional

from . import spec
from .circuit import DIODE_MODELS, MOVES
from .evaluate import Evaluation

EXAMPLE_CIRCUIT = {
    "move": "new_topology",
    "name": "short label for this design",
    "rationale": "what you changed and why it should fix the failing checks",
    "done": False,
    "components": [
        {"id": "D1", "type": "D", "nodes": ["pzp", "out"], "model": "DSCH"},
        {"id": "C1", "type": "C", "nodes": ["out", "0"], "value": 2.2e-6},
        {"id": "L1", "type": "L", "nodes": ["pzp", "n1"], "value": 4.7e-3},
        {"id": "S1", "type": "S", "nodes": ["n1", "pzn"], "ctrl": "G1"},
        {"id": "G1", "type": "SYNC", "ton": 3.4e-5, "phase": 0.0, "edges": "both"},
    ],
}
EXAMPLE_JSON = {"proposals": [EXAMPLE_CIRCUIT]}

# For the neutral_prompt variant: the same JSON syntax with a meaningless R-C network, so the example
# carries no piece of a known interface (EXAMPLE_CIRCUIT's L-S-SYNC branch is the SSHI branch).
NEUTRAL_EXAMPLE_JSON = {"proposals": [{
    "move": "new_topology",
    "name": "short label for this design",
    "rationale": "what you changed and why it should fix the failing checks",
    "done": False,
    "components": [
        {"id": "R1", "type": "R", "nodes": ["pzp", "n1"], "value": 1e3},
        {"id": "C1", "type": "C", "nodes": ["n1", "out"], "value": 1e-6},
        {"id": "C2", "type": "C", "nodes": ["out", "pzn"], "value": 1e-6},
    ],
}]}

_DIODE_WIRING = """     Orientation matters:
       full bridge: ["pzp", "out"], ["pzn", "out"], ["0", "pzp"], ["0", "pzn"] (return diodes have
       their anode on ground);
       zener clamp on out: ["0", "out"] (cathode on out, so it is reverse-biased and breaks down at
       3.3 V). ["out", "0"] would be forward-biased and hold out near 0.7 V; it is rejected."""
_DIODE_WIRING_NEUTRAL = """     Orientation matters: a diode with nodes ["a", "b"] conducts forward from a to b; a DZ33 with
       nodes ["a", "b"] also conducts in reverse once V(b) - V(a) exceeds 3.3 V. A diode forward-biased
       from out to ground would hold out near 0.7 V; it is rejected."""

REPEATED_TEXT = {
    "pinned": "the output stays pinned near 0 V (a wiring or orientation error, not a value problem)",
    "sim_failed": "the simulation fails",
    "underpower": "too little power reaches the output on some conditions",
    "overvoltage": "the output exceeds the maximum voltage on some conditions",
}


def _f(v, fmt="{:.3g}") -> str:
    return "-" if v is None else fmt.format(v)


def condition_table(ev: Evaluation, conditions) -> str:
    """Fixed-width table: measurements and pass/fail per criterion for each condition."""
    crit = [c.id for c in spec.CRITERIA]
    head = f"{'cond':<5}{'vavg V':>8}{'vmax V':>8}{'vpp mV':>8}{'tup s':>8}{'Pload uW':>10}  " + \
        " ".join(f"{c:<8}" for c in crit)
    rows = [head]
    by = {(c.condition, c.criterion): c for c in ev.checks}
    for cond in conditions:
        m = ev.meas.get(cond.id, {})
        if not ev.sim_ok.get(cond.id, False):
            rows.append(f"{cond.id:<5}  simulation failed")
            continue
        vpp = m.get("vpp")
        pl = m.get("pload")
        flags = " ".join(f"{('ok' if by[(cond.id, c)].passed else 'FAIL'):<8}" for c in crit if (cond.id, c) in by)
        rows.append(f"{cond.id:<5}{_f(m.get('vavg')):>8}{_f(m.get('vmax')):>8}"
                    f"{_f(None if vpp is None else vpp * 1e3):>8}{_f(m.get('tup')):>8}"
                    f"{_f(None if pl is None else pl * 1e6):>10}  {flags}")
    return "\n".join(rows)


def system_prompt(reference_eval: Evaluation, per_round: int = 3, screen: bool = True, size_budget: int = 48,
                  neutral: bool = False) -> str:
    """neutral: the neutral_prompt variant, without the fragments of the textbook answer (SSHI branch in
    the JSON example, its switch-timing formula, bridge and zener-clamp wiring examples)."""
    conds = spec.search_conditions()
    sc = spec.SCREEN
    screen_text = (f"""- Each proposal is first SCREENED: with out fixed at {sc['vstore']:g} V, the net power it delivers is
  measured on {', '.join(sc['conditions'])} for its proposed values and a few automatic value presets.
  If the best preset delivers less than {sc['alpha'] * 100:.0f} % of the load's need (V^2/RL) on any of them,
  the design is reported back with those powers and is not tuned or simulated further.
""" if screen else "")
    how_many = ("exactly 1 design" if per_round == 1 else
                f"up to {per_round} designs with DIFFERENT connectivity (different structures, not value variants)")
    ctable = "\n".join(
        f"  {c.id}: {c.label}; Ip = {c.ip * 1e6:g} uA peak, f = {c.freq:g} Hz, Cp = {c.cp * 1e9:g} nF, "
        f"RL = {c.rl / 1e3:g} kOhm, temperature {c.temp:g} C" for c in conds)
    crit = "\n".join(f"  {c.id}: {c.meas} {c.op} {c.limit:g} {c.unit} ({c.description})" for c in spec.CRITERIA)
    L = spec.LIMITS
    nom = conds[0]
    voc_nom = nom.ip / (2 * math.pi * nom.freq * nom.cp)
    ton_hint = "" if neutral else "\n     For L-Cp inversion, ton is about pi*sqrt(L*Cp)."
    diode_wiring = _DIODE_WIRING_NEUTRAL if neutral else _DIODE_WIRING
    example = json.dumps(NEUTRAL_EXAMPLE_JSON if neutral else EXAMPLE_JSON, indent=1)
    return f"""You are an expert power-electronics designer synthesising the interface circuit of a
piezoelectric energy harvester. You work by experiment: you propose a circuit, it is simulated in
LTspice under several operating conditions, and you receive the measurements.

GOAL
A piezo transducer must power a sensor-node load RL from a storage capacitor at node "out".
Under EVERY operating condition below, starting from 0 V (cold start) and simulating 0.8 s:
{crit}
Measurement windows: vavg and vpp over 0.7-0.8 s; vmax over the whole run; tup = first time
V(out) reaches {spec.vmin():g} V (missing if never); dv = |mean(0.7-0.8 s) - mean(0.6-0.7 s)|.

PIEZO MODEL AND OPERATING CONDITIONS
The piezo is a sinusoidal current source Ip*sin(2*pi*f*t) in parallel with its capacitance Cp and a
20 MOhm leakage resistance, between nodes pzp and pzn (Cp = {nom.cp * 1e9:g} nF at {nom.id}).
Its open-circuit voltage amplitude is Ip/(2*pi*f*Cp), about {voc_nom:.2g} V at {nom.id}; compare it with the
output window and the diode drops.
{ctable}

TEST BENCH (fixed, added automatically - do not include these)
- the piezo model between pzp and pzn; the load RL from out to 0;
- for every SYNC controller you use, a 0.5 uA supply current drawn from out (its power cost);
- a 1 GOhm resistor to 0 from pzp, pzn and every internal node (prevents floating nodes).

COMPONENTS YOU MAY USE (at most {L['max_components']} components)
- R  resistor, value {L['R'][0]:g}..{L['R'][1]:g} Ohm, nodes [a, b]
- C  capacitor, value {L['C'][0]:g}..{L['C'][1]:g} F, nodes [a, b]
- L  inductor, value {L['L'][0]:g}..{L['L'][1]:g} H; it has series resistance 2 Ohm + 5 Ohm per mH
- D  diode, nodes [anode, cathode]: forward current flows from the first node to the second.
     Model one of {', '.join(DIODE_MODELS)}:
     DSCH = low-drop Schottky (~0.25 V at uA), DSI = silicon small-signal (~0.5 V at uA),
     DZ33 = 3.3 V zener (reverse breakdown 3.3 V, conducts ~1 uA at 3.3 V and much more above)
{diode_wiring}
- S  switch, nodes [a, b], "ctrl": id of a SYNC; Ron = 2 Ohm, Roff = 1 GOhm (at most {L['max_switches']})
- SYNC ideal synchronous controller (no nodes, at most {L['max_sync']}): closes its switches for "ton"
     seconds ({L['ton'][0]:g}..{L['ton'][1]:g}) at the piezo voltage extrema, which occur at the zero
     crossings of the piezo current. "edges": "both" (every half period), "pos" (positive peak only)
     or "neg" (negative peak only). "phase" shifts the pulses by that fraction of the excitation
     period ({L['phase'][0]}..{L['phase'][1]}). It tracks the excitation frequency automatically.{ton_hint}
Nodes: "0" is ground; pzp, pzn are the piezo terminals; out is the load/storage node; name any other
nodes yourself (lower-case, e.g. n1, mid). Every node needs at least two connections, and out must
connect to the piezo through your circuit.

REFERENCE DESIGN: FBR (full-bridge rectifier, 4 x DSCH, 2.2 uF on out). Its results:
{condition_table(reference_eval, conds)}

HOW TO WORK
- Component values are optimised automatically (an evolution strategy, up to {size_budget} full
  evaluations per structure, running while you think), so spend your reasoning on circuit
  CONNECTIVITY (topology): which structure can meet every condition. A structure that was already
  explored is not simulated again, whatever its values.
{screen_text}- Each round, propose {how_many}.
- Classify each design with "move": new_topology or modify_topology, and explain the expected effect
  in "rationale". Set "done": true only when you believe no further structural change can improve on
  the best design so far.
- Reply with ONE JSON object only, in this form:
{example}
"""


def required_move(moves: List[str]) -> Optional[str]:
    """Force a structural change after three value-only proposals in a row."""
    if len(moves) >= 3 and all(m == "resize" for m in moves[-3:]):
        return "new_topology or modify_topology"
    return None


def _hints(d: dict) -> str:
    hs = d.get("hints") or []
    return ("\nwhat this means:\n" + "\n".join(f"- {h}" for h in hs)) if hs else ""


def _design_block(d: dict) -> str:
    extra = ""
    if d.get("screen"):
        extra += f"\nscreen (out fixed at {spec.SCREEN['vstore']:g} V): {d['screen']}"
    if d.get("sizing"):
        extra += f"\nvalue sizing: {d['sizing']}"
    return (f"[{d['id']}] {d['name']}  (topology {d['topo_hash']}, score {d['scalar']:.2f}, "
            f"conditions passed {d['cond_pass']}/{len(spec.search_conditions())})\n"
            f"{d['circuit_text']}\n{d['table']}\n"
            f"failing: {d['diagnosis'] or 'nothing - all checks pass'}{extra}{_hints(d)}")


def _result_block(k: int, d: dict) -> str:
    name = d.get("name", "")
    kind = d.get("kind")
    if kind is None:   # older dict form
        kind = ("invalid" if d.get("invalid_problems") else "duplicate" if d.get("duplicate")
                else "error" if d.get("error") else "evaluated")
    head = f"Design {k} '{name}': "
    if kind == "invalid":
        return head + "rejected before simulation:\n- " + "\n- ".join(d["invalid_problems"])
    if kind == "duplicate":
        return head + (f"duplicate: same structure as an earlier design ({d.get('id', '?')}); nothing new was simulated. "
                       f"Values are tuned automatically, so propose a different structure.")
    if kind == "error":
        return f"Your previous request failed: {d['error']}"
    if kind == "screen_failed":
        return (head + f"failed the screen and was not tuned (topology {d.get('topo_hash', '?')}).\n"
                f"{d.get('circuit_text', '')}\nscreen (out fixed at {spec.SCREEN['vstore']:g} V): {d.get('screen', '')}{_hints(d)}")
    return head + "simulated with the best screening preset (it is being tuned):\n" + _design_block(d)


def iteration_prompt(iteration: int, max_rounds: int, top: List[dict], last, explored: List[dict],
                     required: Optional[str], repeated: Optional[List[str]] = None) -> str:
    parts = [f"Round {iteration} of {max_rounds}."]
    if isinstance(last, dict):
        last = [last]
    if not last and iteration <= 1:
        parts.append("This is your first round: choose the structures you think most likely to meet "
                     "every condition.")
    elif last:
        parts.append("RESULTS OF YOUR PREVIOUS ROUND:\n\n" +
                     "\n\n".join(_result_block(k, d) for k, d in enumerate(last, 1)))
    if repeated:
        parts.append("REPEATED PROBLEM: your last three designs all show the same failure: " +
                     "; ".join(REPEATED_TEXT.get(c, c) + f" [{c}]" for c in repeated) +
                     ". Change the part of the circuit responsible for it rather than its values.")
    if top:
        parts.append("BEST DESIGNS SO FAR (values already tuned):\n\n" + "\n\n".join(_design_block(d) for d in top))
    if explored:
        parts.append("Topologies explored so far (hash: name, best score):\n" + "\n".join(
            f"  {e['topo_hash']}: {e['name']} ({e['best_scalar']:.2f})" for e in explored))
    if required:
        parts.append(f"Your last three designs only changed values. This round MUST change the "
                     f"connectivity (move = {required}).")
    parts.append("Reply with one JSON object only.")
    return "\n\n".join(parts)


def repair_messages(system: str, user: str, bad_answer: str, problems: List[str]) -> List[dict]:
    return [{"role": "system", "content": system},
            {"role": "user", "content": user},
            {"role": "assistant", "content": bad_answer[:4000]},
            {"role": "user", "content": "That reply could not be used:\n- " + "\n- ".join(problems) +
             "\nReply again with one corrected JSON object only."}]
