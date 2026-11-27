import math
import random
import unittest

from piezo_synth.circuit import design_hash, get_param, with_param
from piezo_synth.evaluate import Evaluation
from piezo_synth.netlist import witness_circuit
from piezo_synth.sizer import Sizer

OPT_TON, OPT_C = 34e-6, 4.7e-6


def objective(c):
    d = abs(math.log(get_param(c, "G1", "ton") / OPT_TON)) + abs(math.log(get_param(c, "C1", "value") / OPT_C))
    return Evaluation(scalar=-d, all_pass=d < 0.05)


def drive(sz, max_gens=200):
    gens = 0
    while not sz.done and gens < max_gens:
        batch = sz.ask()
        sz.tell(batch, [objective(c) for c in batch])
        gens += 1
    return gens


def start():
    c = with_param(witness_circuit(), "G1", "ton", 8e-6)
    return with_param(c, "C1", "value", 0.5e-6)


class SizerTest(unittest.TestCase):
    def test_improves_and_stops_when_spec_met(self):
        c = start()
        sz = Sizer(c, objective(c), budget=400, rng=random.Random(3), lam=8)
        drive(sz)
        self.assertTrue(sz.done)
        self.assertEqual(sz.reason, "spec_met")
        self.assertTrue(sz.best_ev.all_pass)
        self.assertLess(sz.n_evals, 400)

    def test_budget_is_respected_exactly(self):
        c = start()
        sz = Sizer(c, objective(c), budget=20, rng=random.Random(1), lam=8)
        drive(sz)
        self.assertEqual(sz.n_evals, 20)
        self.assertEqual(sz.reason, "budget")
        self.assertGreater(sz.best_ev.scalar, objective(c).scalar)

    def test_batch_has_distinct_new_designs(self):
        c = start()
        sz = Sizer(c, objective(c), budget=100, rng=random.Random(2), lam=8)
        batch = sz.ask()
        hashes = {design_hash(x) for x in batch}
        self.assertEqual(len(hashes), len(batch))
        self.assertNotIn(design_hash(c), hashes)

    def test_no_parameters_means_done(self):
        from piezo_synth.circuit import Circuit, Component
        c = Circuit(name="diodes only", components=[Component("D1", "D", ("pzp", "out"), model="DSCH"),
                                                    Component("D2", "D", ("0", "pzp"), model="DSCH")])
        sz = Sizer(c, Evaluation(), budget=10, rng=random.Random(1))
        self.assertTrue(sz.done)
        self.assertEqual(sz.ask(), [])

    def test_already_passing_start_is_done(self):
        c = with_param(with_param(witness_circuit(), "G1", "ton", OPT_TON), "C1", "value", OPT_C)
        sz = Sizer(c, objective(c), budget=10, rng=random.Random(1))
        self.assertTrue(sz.done)
        self.assertEqual(sz.reason, "spec_met")


if __name__ == "__main__":
    unittest.main()
