"""Prompts for the model. Rebuilt from the search state every iteration (no growing chat history).

Only search conditions appear here: the held-out conditions are never shown to the model.
"""
from __future__ import annotations

import json
from typing import List, Optional

from . import spec
from .circuit import DIODE_MODELS, MOVES
from .evaluate import Evaluation

EXAMPLE_JSON = {
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


def system_prompt(reference_eval: Evaluation) -> str:
    conds = spec.search_conditions()
    ctable = "\n".join(
        f"  {c.id}: {c.label}; Ip = {c.ip * 1e6:g} uA peak, f = {c.freq:g} Hz, Cp = {c.cp * 1e9:g} nF, "
        f"RL = {c.rl / 1e3:g} kOhm, temperature {c.temp:g} C" for c in conds)
    crit = "\n".join(f"  {c.id}: {c.meas} {c.op} {c.limit:g} {c.unit} ({c.description})" for c in spec.CRITERIA)
    L = spec.LIMITS
    return f"""You are an expert power-electronics designer synthesising the interface circuit of a
piezoelectric energy harvester. You work by experiment: you propose a circuit, it is simulated in
LTspice under several operating conditions, and you receive the measurements.

GOAL
A piezo transducer must power a sensor-node load RL from a storage capacitor at node "out".
Under EVERY operating condition below, starting from 0 V (cold start) and simulating 0.8 s:
{crit}
Measurement windows: vavg and vpp over 0.7-0.8 s; vmax over the whole run; tup = first time
V(out) reaches 1.8 V (missing if never); dv = |mean(0.7-0.8 s) - mean(0.6-0.7 s)|.

PIEZO MODEL AND OPERATING CONDITIONS
The piezo is a sinusoidal current source Ip*sin(2*pi*f*t) in parallel with its capacitance Cp and a
20 MOhm leakage resistance, between nodes pzp and pzn (Cp = 25 nF nominal).
Its open-circuit voltage amplitude is Ip/(2*pi*f*Cp), about 3.2 V at nominal: low, so diode drops matter.
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
     Orientation matters:
       full bridge: ["pzp", "out"], ["pzn", "out"], ["0", "pzp"], ["0", "pzn"] (return diodes have
       their anode on ground);
       zener clamp on out: ["0", "out"] (cathode on out, so it is reverse-biased and breaks down at
       3.3 V). ["out", "0"] would be forward-biased and hold out near 0.7 V; it is rejected.
- S  switch, nodes [a, b], "ctrl": id of a SYNC; Ron = 2 Ohm, Roff = 1 GOhm (at most {L['max_switches']})
- SYNC ideal synchronous controller (no nodes, at most {L['max_sync']}): closes its switches for "ton"
     seconds ({L['ton'][0]:g}..{L['ton'][1]:g}) at the piezo voltage extrema, which occur at the zero
     crossings of the piezo current. "edges": "both" (every half period), "pos" (positive peak only)
     or "neg" (negative peak only). "phase" shifts the pulses by that fraction of the excitation
     period ({L['phase'][0]}..{L['phase'][1]}). It tracks the excitation frequency automatically.
     For L-Cp inversion, ton is about pi*sqrt(L*Cp).
Nodes: "0" is ground; pzp, pzn are the piezo terminals; out is the load/storage node; name any other
nodes yourself (lower-case, e.g. n1, mid). Every node needs at least two connections, and out must
connect to the piezo through your circuit.

REFERENCE DESIGN: FBR (full-bridge rectifier, 4 x DSCH, 2.2 uF on out). Its results:
{condition_table(reference_eval, conds)}

HOW TO WORK
- Component values are tuned automatically by a numerical optimiser after each proposal, so spend
  your reasoning on circuit CONNECTIVITY (topology): which structure can meet every condition.
- Classify each proposal with "move": {', '.join(MOVES)} (resize = same connectivity, new values).
- Explain the expected effect in "rationale". Set "done": true only when you believe no further
  structural change can improve on the best design so far.
- Reply with ONE JSON object only, in this form:
{json.dumps(EXAMPLE_JSON, indent=1)}
"""


def required_move(moves: List[str]) -> Optional[str]:
    """Force a structural change after three value-only proposals in a row."""
    if len(moves) >= 3 and all(m == "resize" for m in moves[-3:]):
        return "new_topology or modify_topology"
    return None


def _design_block(d: dict) -> str:
    return (f"[{d['id']}] {d['name']}  (topology {d['topo_hash']}, score {d['scalar']:.2f}, "
            f"conditions passed {d['cond_pass']}/{len(spec.search_conditions())})\n"
            f"{d['circuit_text']}\n{d['table']}\n"
            f"failing: {d['diagnosis'] or 'nothing - all checks pass'}")


def iteration_prompt(iteration: int, max_proposals: int, top: List[dict], last: Optional[dict],
                     explored: List[dict], required: Optional[str]) -> str:
    parts = [f"Proposal {iteration} of {max_proposals}."]
    if last is None:
        parts.append("This is your first proposal: choose the topology you think most likely to meet "
                     "every condition.")
    elif last.get("invalid_problems"):
        parts.append("Your previous proposal was rejected before simulation:\n- " +
                     "\n- ".join(last["invalid_problems"]))
    elif last.get("duplicate"):
        parts.append(f"Your previous proposal '{last.get('name', '')}' was a duplicate of an earlier design "
                     f"({last.get('id', '?')}); nothing new was simulated. Propose something different.")
    elif last.get("error"):
        parts.append(f"Your previous request failed: {last['error']}")
    else:
        parts.append("Result of your previous proposal, with the values you proposed (it is tuned automatically "
                     "while you think; tuned versions appear under BEST DESIGNS):\n" + _design_block(last))
    if top:
        parts.append("BEST DESIGNS SO FAR (values already tuned):\n\n" + "\n\n".join(_design_block(d) for d in top))
    if explored:
        parts.append("Topologies explored so far (hash: name, best score):\n" + "\n".join(
            f"  {e['topo_hash']}: {e['name']} ({e['best_scalar']:.2f})" for e in explored))
    if required:
        parts.append(f"Your last three proposals only changed values. This proposal MUST change the "
                     f"connectivity (move = {required}).")
    parts.append("Reply with one JSON object only.")
    return "\n\n".join(parts)


def repair_messages(system: str, user: str, bad_answer: str, problems: List[str]) -> List[dict]:
    return [{"role": "system", "content": system},
            {"role": "user", "content": user},
            {"role": "assistant", "content": bad_answer[:4000]},
            {"role": "user", "content": "That reply could not be used:\n- " + "\n- ".join(problems) +
             "\nReply again with one corrected JSON object only."}]
