"""Model-free baseline: proposes random valid circuits over the same vocabulary, through the same
screen -> evaluation -> sizing pipeline, so a run with it measures what the language model adds."""
from __future__ import annotations

import json
import math
import random
from typing import List, Optional

from .circuit import DIODE_MODELS, EDGES, Circuit, Component, to_dict, validate
from .llm import LLMReply
from .spec import LIMITS

TYPE_WEIGHTS = {"D": 0.35, "C": 0.2, "L": 0.15, "S": 0.15, "R": 0.15}


def _logu(rng: random.Random, lo: float, hi: float) -> float:
    return math.exp(rng.uniform(math.log(lo), math.log(hi)))


def _attempt(rng: random.Random) -> Circuit:
    internal = [f"n{k}" for k in range(1, rng.randint(0, 3) + 1)]
    pool = ["0", "pzp", "pzn", "out", *internal]
    n = rng.randint(4, 12)
    types = rng.choices(list(TYPE_WEIGHTS), weights=list(TYPE_WEIGHTS.values()), k=n)
    n_sw = 0
    comps: List[Component] = []
    count = {}
    for t in types:
        if t == "S" and n_sw >= LIMITS["max_switches"]:
            t = "D"
        a, b = rng.sample(pool, 2)
        count[t] = count.get(t, 0) + 1
        cid = f"{t}{count[t]}"
        if t in ("R", "C", "L"):
            comps.append(Component(cid, t, (a, b), value=_logu(rng, *LIMITS[t])))
        elif t == "D":
            comps.append(Component(cid, t, (a, b), model=rng.choice(DIODE_MODELS)))
        else:
            n_sw += 1
            comps.append(Component(cid, t, (a, b), ctrl="G1"))
    if n_sw:
        comps.append(Component("G1", "SYNC", (), ton=_logu(rng, *LIMITS["ton"]),
                               phase=rng.uniform(*LIMITS["phase"]), edges=rng.choice(EDGES)))
    return Circuit(name="random", components=comps, move="new_topology", rationale="random baseline")


def random_circuit(rng: random.Random, max_tries: int = 20000) -> Circuit:
    for _ in range(max_tries):
        c = _attempt(rng)
        if not validate(c):
            return c
    raise RuntimeError("no valid random circuit found")


class RandomProposer:
    """Stands in for the model: same ask() interface, zero tokens, instant replies."""

    def __init__(self, seed: int = 1, per_round: int = 3):
        self.rng = random.Random(seed)
        self.per_round = per_round
        self.n = 0

    def ask(self, messages, think: bool, max_tokens: Optional[int] = None, temperature: Optional[float] = None,
            timeout: Optional[float] = None) -> LLMReply:
        props = []
        for _ in range(self.per_round):
            self.n += 1
            c = random_circuit(self.rng)
            c.name = f"random-{self.n:03d}"
            props.append(to_dict(c))
        return LLMReply(answer=json.dumps({"proposals": props}), seconds=0.0, prompt_tokens=0,
                        completion_tokens=0, reasoning_tokens=0, finish="stop")
