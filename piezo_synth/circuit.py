"""Circuit representation proposed by the model: parse, validate, canonicalise, hash, edit values.

A circuit is a list of components over a fixed vocabulary, connected through named nodes.
Reserved nodes: "0" (ground), "pzp"/"pzn" (piezo terminals), "out" (storage/load node).
The test bench (piezo model, load, controller supply sinks) is added by netlist.py.
"""
from __future__ import annotations

import copy
import hashlib
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .spec import LIMITS

ALLOWED_TYPES = ("R", "C", "L", "D", "S", "SYNC")
DIODE_MODELS = ("DSCH", "DSI", "DZ33")
RESERVED_NODES = ("0", "pzp", "pzn", "out")
MOVES = ("new_topology", "modify_topology", "resize")
EDGES = ("both", "pos", "neg")
TWO_TERMINAL = ("R", "C", "L", "D", "S")
VALUED = ("R", "C", "L")
# connections the harness itself makes to each reserved node (piezo model, load)
HARNESS_CONNECTIONS = {"pzp": 1, "pzn": 1, "out": 1}

_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,7}$")
_NODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,11}$")
_SUFFIX = {"f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "m": 1e-3,
           "k": 1e3, "meg": 1e6, "g": 1e9, "t": 1e12}


class CircuitError(ValueError):
    def __init__(self, problems: List[str]):
        super().__init__("; ".join(problems))
        self.problems = list(problems)


@dataclass
class Component:
    id: str
    type: str
    nodes: tuple = ()
    value: Optional[float] = None
    model: Optional[str] = None
    ctrl: Optional[str] = None
    ton: Optional[float] = None
    phase: Optional[float] = None
    edges: Optional[str] = None


@dataclass
class Circuit:
    name: str
    components: List[Component] = field(default_factory=list)
    move: str = "new_topology"
    rationale: str = ""
    done: bool = False


def parse_value(v) -> Optional[float]:
    """A number, or a SPICE-style string such as '2.2u', '4.7meg', '10k'. None if unparseable."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if not isinstance(v, str):
        return None
    s = v.strip().lower().replace(" ", "")
    m =re.match(r"^([-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?)(meg|[fpnuµmkgt])?[a-z]*$", s)
    if not m:
        return None
    return float(m.group(1)) * (_SUFFIX[m.group(2)] if m.group(2) else 1.0)


# ---------------------------------------------------------------- parsing and validation

def parse_circuit(obj: dict) -> Circuit:
    """Build a Circuit from the model's JSON object; raise CircuitError listing every problem."""
    problems: List[str] = []
    if not isinstance(obj, dict):
        raise CircuitError(["the reply is not a JSON object"])
    comps_in = obj.get("components")
    if not isinstance(comps_in, list) or not comps_in:
        raise CircuitError(["'components' must be a non-empty list"])
    comps: List[Component] = []
    for k, raw in enumerate(comps_in):
        if not isinstance(raw, dict):
            problems.append(f"component #{k + 1} is not an object")
            continue
        cid = str(raw.get("id", f"#{k + 1}"))
        ctype = str(raw.get("type", "")).upper()
        nodes = raw.get("nodes", [])
        if not isinstance(nodes, list):
            problems.append(f"{cid}: 'nodes' must be a list")
            nodes = []
        num = {}
        for f in ("value", "ton", "phase"):
            if raw.get(f) is not None:
                num[f] = parse_value(raw[f])
                if num[f] is None:
                    problems.append(f"{cid}: {f}={raw[f]!r} is not a number")
        comps.append(Component(
            id=cid, type=ctype, nodes=tuple(str(n) for n in nodes),
            value=num.get("value"), model=(str(raw["model"]).upper() if raw.get("model") else None),
            ctrl=(str(raw["ctrl"]) if raw.get("ctrl") else None),
            ton=num.get("ton"), phase=num.get("phase"),
            edges=(str(raw["edges"]).lower() if raw.get("edges") else None)))
    c = Circuit(name=str(obj.get("name", "unnamed"))[:80], components=comps,
                move=str(obj.get("move", "new_topology")), rationale=str(obj.get("rationale", "")),
                done=bool(obj.get("done", False)))
    problems += validate(c)
    if problems:
        raise CircuitError(problems)
    return c


def _in(lo_hi, v) -> bool:
    return v is not None and lo_hi[0] <= v <= lo_hi[1]


def validate(c: Circuit) -> List[str]:
    """Every rule violation as a human-readable line naming the component."""
    p: List[str] = []
    if c.move not in MOVES:
        p.append(f"move={c.move!r} must be one of {', '.join(MOVES)}")
    ids = [x.id for x in c.components]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        p.append(f"{dup}: duplicate id")
    syncs = {x.id for x in c.components if x.type == "SYNC"}
    used_syncs = set()
    for x in c.components:
        if not _ID_RE.match(x.id):
            p.append(f"{x.id}: id must be a letter followed by up to 7 letters/digits/_")
        if x.type not in ALLOWED_TYPES:
            p.append(f"{x.id}: type {x.type!r} is not allowed (use {', '.join(ALLOWED_TYPES)})")
            continue
        if x.type in TWO_TERMINAL:
            if len(x.nodes) != 2:
                p.append(f"{x.id}: needs exactly 2 nodes, got {len(x.nodes)}")
            elif x.nodes[0] == x.nodes[1]:
                p.append(f"{x.id}: both terminals on node {x.nodes[0]}")
            for n in x.nodes:
                if n != "0" and not _NODE_RE.match(n):
                    p.append(f"{x.id}: node name {n!r} must be lower-case, start with a letter, max 12 chars, or '0'")
        elif x.nodes:
            p.append(f"{x.id}: SYNC takes no nodes")
        if x.type in VALUED and not _in(LIMITS[x.type], x.value):
            lo, hi = LIMITS[x.type]
            p.append(f"{x.id}: value {x.value} outside [{lo:g}, {hi:g}]")
        if x.type == "D" and x.model not in DIODE_MODELS:
            p.append(f"{x.id}: diode model must be one of {', '.join(DIODE_MODELS)}")
        if x.type == "S":
            if x.ctrl not in syncs:
                p.append(f"{x.id}: ctrl must name a SYNC component (got {x.ctrl!r})")
            else:
                used_syncs.add(x.ctrl)
        if x.type == "SYNC":
            if not _in(LIMITS["ton"], x.ton):
                p.append(f"{x.id}: ton {x.ton} outside [{LIMITS['ton'][0]:g}, {LIMITS['ton'][1]:g}] s")
            if not _in(LIMITS["phase"], 0.0 if x.phase is None else x.phase):
                p.append(f"{x.id}: phase {x.phase} outside [{LIMITS['phase'][0]}, {LIMITS['phase'][1]}] periods")
            if (x.edges or "both") not in EDGES:
                p.append(f"{x.id}: edges must be one of {', '.join(EDGES)}")
    for s in sorted(syncs - used_syncs):
        p.append(f"{s}: SYNC controller is not used by any switch")
    # connectivity
    count: Dict[str, int] = dict(HARNESS_CONNECTIONS)
    for x in c.components:
        if x.type in TWO_TERMINAL and len(x.nodes) == 2:
            for n in x.nodes:
                count[n] = count.get(n, 0) + 1
    for r in ("pzp", "pzn", "out"):
        if count.get(r, 0) <= HARNESS_CONNECTIONS[r]:
            p.append(f"node {r} is not connected to any component")
    for n, k in sorted(count.items()):
        if n not in RESERVED_NODES and k < 2:
            p.append(f"node {n} has only one connection (dangling)")
    if not _connected(c, "out", "pzp"):
        p.append("node out is not connected to the piezo (pzp) through the circuit")
    n_sw = sum(x.type == "S" for x in c.components)
    if len(c.components) > LIMITS["max_components"]:
        p.append(f"{len(c.components)} components; at most {LIMITS['max_components']} allowed")
    if n_sw > LIMITS["max_switches"]:
        p.append(f"{n_sw} switches; at most {LIMITS['max_switches']} allowed")
    if len(syncs) > LIMITS["max_sync"]:
        p.append(f"{len(syncs)} SYNC controllers; at most {LIMITS['max_sync']} allowed")
    return p


def _connected(c: Circuit, a: str, b: str) -> bool:
    adj: Dict[str, set] = {"pzp": {"pzn"}, "pzn": {"pzp"}}
    for x in c.components:
        if x.type in TWO_TERMINAL and len(x.nodes) == 2:
            u, v = x.nodes
            adj.setdefault(u, set()).add(v)
            adj.setdefault(v, set()).add(u)
    seen, stack = {a}, [a]
    while stack:
        for nb in adj.get(stack.pop(), ()):
            if nb not in seen:
                seen.add(nb)
                stack.append(nb)
    return b in seen


# ---------------------------------------------------------------- canonical form and hashes

def _h(s: str) -> str:
    return hashlib.sha1(s.encode()).hexdigest()[:16]


def _pins(x: Component) -> List[Tuple[str, str]]:
    """(node, role) pairs; diodes are polar (anode/cathode), others are not."""
    if x.type == "D":
        return [(x.nodes[0], "a"), (x.nodes[1], "k")]
    return [(n, "x") for n in x.nodes]


def canonical(c: Circuit) -> Circuit:
    """Same circuit with internal nodes renamed n1..nk and ids renamed by type, in a form that does
    not depend on the names or order the model chose."""
    comps = [copy.copy(x) for x in c.components]
    nodes = sorted({n for x in comps for n in x.nodes})
    label = {n: (n if n in RESERVED_NODES else "int") for n in nodes}
    for _ in range(3):
        new = {}
        for n in nodes:
            ctx = []
            for x in comps:
                pins = _pins(x) if x.type in TWO_TERMINAL else []
                for node, role in pins:
                    if node == n:
                        others = [label[o] for o, _r in pins if o != n]
                        ctx.append(f"{x.type}/{x.model}/{role}/{','.join(others)}")
            new[n] = _h(label[n] + "|" + ";".join(sorted(ctx)))
        label = {n: (n if n in RESERVED_NODES else new[n]) for n in nodes}

    by_id = {x.id: x for x in comps}

    def sig(x: Component) -> str:
        if x.type == "SYNC":
            sw = sorted(sig(s) for s in comps if s.type == "S" and s.ctrl == x.id)
            return f"SYNC/{x.edges or 'both'}/{'+'.join(sw)}"
        pins = _pins(x)
        labs = [f"{label[n]}{r}" for n, r in pins]
        if x.type != "D":
            labs.sort()
        extra = ""
        if x.type == "S" and x.ctrl in by_id:
            extra = "/" + (by_id[x.ctrl].edges or "both")
        return f"{x.type}/{x.model}/{','.join(labs)}{extra}"

    order = sorted(range(len(comps)), key=lambda i: (sig(comps[i]), i))
    rename: Dict[str, str] = {}
    k = 0
    for i in order:
        x = comps[i]
        for n in (x.nodes if x.type == "D" else sorted(x.nodes, key=lambda m: label[m])):
            if n not in RESERVED_NODES and n not in rename:
                k += 1
                rename[n] = f"n{k}"
    out: List[Component] = []
    counters: Dict[str, int] = {}
    id_map: Dict[str, str] = {}
    for i in order:
        x = comps[i]
        prefix = "G" if x.type == "SYNC" else x.type
        counters[prefix] = counters.get(prefix, 0) + 1
        id_map[x.id] = f"{prefix}{counters[prefix]}"
    for i in order:
        x = copy.copy(comps[i])
        nn = tuple(rename.get(n, n) for n in x.nodes)
        if x.type in TWO_TERMINAL and x.type != "D":
            nn = tuple(sorted(nn))
        x.nodes = nn
        x.id = id_map[x.id]
        if x.ctrl:
            x.ctrl = id_map.get(x.ctrl, x.ctrl)
        if x.type == "SYNC":
            x.edges = x.edges or "both"
            x.phase = 0.0 if x.phase is None else x.phase
        out.append(x)
    return Circuit(name=c.name, components=out, move=c.move, rationale=c.rationale, done=c.done)


def _struct_line(x: Component) -> str:
    return f"{x.id} {x.type} {' '.join(x.nodes)} m={x.model} ctrl={x.ctrl} e={x.edges}"


def _value_line(x: Component) -> str:
    vals = [f"{v:.3g}" if v is not None else "-" for v in (x.value, x.ton, x.phase)]
    return " ".join(vals)


def topology_hash(c: Circuit) -> str:
    cc = canonical(c)
    return hashlib.sha256("\n".join(_struct_line(x) for x in cc.components).encode()).hexdigest()[:12]


def design_hash(c: Circuit) -> str:
    cc = canonical(c)
    text = "\n".join(_struct_line(x) + " | " + _value_line(x) for x in cc.components)
    return hashlib.sha256(text.encode()).hexdigest()[:12]


# ---------------------------------------------------------------- serialisation and value edits

def to_dict(c: Circuit) -> dict:
    comps = []
    for x in c.components:
        d = {"id": x.id, "type": x.type}
        if x.type in TWO_TERMINAL:
            d["nodes"] = list(x.nodes)
        for f in ("value", "model", "ctrl", "ton", "phase", "edges"):
            v = getattr(x, f)
            if v is not None:
                d[f] = v
        comps.append(d)
    return {"move": c.move, "name": c.name, "rationale": c.rationale, "done": c.done, "components": comps}


def numeric_params(c: Circuit) -> List[Tuple[str, str]]:
    out = []
    for x in c.components:
        if x.type in VALUED:
            out.append((x.id, "value"))
        elif x.type == "SYNC":
            out += [(x.id, "ton"), (x.id, "phase")]
    return out


def _find(c: Circuit, cid: str) -> Component:
    for x in c.components:
        if x.id == cid:
            return x
    raise KeyError(cid)


def get_param(c: Circuit, cid: str, fld: str) -> float:
    v = getattr(_find(c, cid), fld)
    return 0.0 if v is None else float(v)


def with_param(c: Circuit, cid: str, fld: str, value: float) -> Circuit:
    """A copy of c with one numeric field changed, clamped to the allowed range."""
    new = copy.deepcopy(c)
    x = _find(new, cid)
    lo, hi = LIMITS[x.type] if fld == "value" else LIMITS[fld]
    setattr(x, fld, min(max(float(value), lo), hi))
    return new


def describe(c: Circuit) -> str:
    """One line per component, SPICE-like, for prompts and reports."""
    lines = []
    for x in c.components:
        if x.type == "SYNC":
            lines.append(f"{x.id} SYNC ton={x.ton:.3g}s phase={x.phase or 0:.3g} edges={x.edges or 'both'}")
        elif x.type == "S":
            lines.append(f"{x.id} S {x.nodes[0]} {x.nodes[1]} ctrl={x.ctrl}")
        elif x.type == "D":
            lines.append(f"{x.id} D {x.nodes[0]} {x.nodes[1]} {x.model}")
        else:
            lines.append(f"{x.id} {x.type} {x.nodes[0]} {x.nodes[1]} {x.value:.3g}")
    return "\n".join(lines)
