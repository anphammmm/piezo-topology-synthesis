import json
import random
import re
import tempfile
import unittest
from pathlib import Path

from piezo_synth import spec
from piezo_synth.baselines import RandomProposer, random_circuit
from piezo_synth.circuit import get_param, parse_circuit, validate
from piezo_synth.netlist import witness_circuit
from piezo_synth.robust import monte_carlo, perturb
from piezo_synth.sim import Simulator
from tests.fakes import FakeBackend

GOOD = dict(vavg=2.5, vavg_prev=2.49, vpp=0.02, vmax=2.6, tup=0.2, pload=1e-5, pext=2e-5)
BAD = dict(GOOD, vavg=1.0, vavg_prev=1.0)


def ton_sensitive(text):
    ton = float(re.search(r"PULSE\(0 1 \S+ 100n 100n (\S+) ", text).group(1))
    return GOOD if abs(ton / 34e-6 - 1) < 0.025 else BAD


class RobustTest(unittest.TestCase):
    def test_perturb_stays_within_tolerance(self):
        rng = random.Random(1)
        w = witness_circuit()
        for _ in range(50):
            p = perturb(w, rng)
            self.assertLessEqual(abs(get_param(p, "L1", "value") / 4.7e-3 - 1), spec.TOLERANCES["L"] + 1e-12)
            self.assertLessEqual(abs(get_param(p, "C1", "value") / 2.2e-6 - 1), spec.TOLERANCES["C"] + 1e-12)
            self.assertLessEqual(abs(get_param(p, "G1", "phase")), spec.TOLERANCES["phase"] + 1e-12)

    def test_monte_carlo_pass_rates(self):
        with tempfile.TemporaryDirectory() as d:
            sim = Simulator(FakeBackend(ton_sensitive), Path(d), workers=4)
            conds = spec.search_conditions()[:2]
            r = monte_carlo(witness_circuit(), conds, sim, random.Random(4), 40, "mc")
        self.assertEqual(r["n"], 40)
        self.assertGreater(r["pass_all"], 0.2)
        self.assertLess(r["pass_all"], 0.8)
        self.assertEqual(sorted(r["per_condition"]), ["S1", "S2"])
        self.assertEqual(r["tolerances"], spec.TOLERANCES)


class RandomBaselineTest(unittest.TestCase):
    def test_random_circuits_are_valid_and_seeded(self):
        a = [random_circuit(random.Random(s)) for s in range(30)]
        for c in a:
            self.assertEqual(validate(c), [])
        b = [random_circuit(random.Random(s)) for s in range(30)]
        self.assertEqual([len(x.components) for x in a], [len(x.components) for x in b])

    def test_proposer_reply_is_parseable(self):
        p = RandomProposer(seed=2, per_round=3)
        r = p.ask([{"role": "user", "content": "x"}], think=True)
        props = json.loads(r.answer)["proposals"]
        self.assertEqual(len(props), 3)
        for d in props:
            parse_circuit(d)
        self.assertEqual((r.prompt_tokens, r.completion_tokens), (0, 0))


if __name__ == "__main__":
    unittest.main()
