import math
import random
import unittest

from piezo_synth.circuit import Circuit, Component, get_param
from piezo_synth.evaluate import Evaluation
from piezo_synth.refine import refine


def circ():
    return Circuit("t", [Component("D1", "D", ("pzp", "out"), model="DSCH"),
                         Component("C1", "C", ("out", "0"), value=1e-7),
                         Component("R1", "R", ("pzn", "0"), value=1e3)])


def fake_eval(c):
    # peak at C1 = 4.7 uF, indifferent to R1
    s = -abs(math.log10(get_param(c, "C1", "value") / 4.7e-6))
    return Evaluation(scalar=s)


class RefineTest(unittest.TestCase):
    def test_refine_improves_and_respects_budget(self):
        c = circ()
        best, ev, tried = refine(c, fake_eval(c), fake_eval, budget=10, rng=random.Random(1))
        self.assertGreater(ev.scalar, fake_eval(c).scalar)
        self.assertLessEqual(len(tried), 10)
        self.assertGreater(get_param(best, "C1", "value"), 1e-7)

    def test_refine_converges_with_big_budget(self):
        c = circ()
        best, ev, _ = refine(c, fake_eval(c), fake_eval, budget=200, rng=random.Random(2))
        self.assertAlmostEqual(get_param(best, "C1", "value") / 4.7e-6, 1.0, delta=0.06)

    def test_refine_stops_when_asked(self):
        n = {"k": 0}

        def stop():
            n["k"] += 1
            return n["k"] > 2
        c = circ()
        _, _, tried = refine(c, fake_eval(c), fake_eval, budget=10, rng=random.Random(1), should_stop=stop)
        self.assertEqual(len(tried), 2)

    def test_refine_no_params_returns_start(self):
        c = Circuit("d", [Component("D1", "D", ("pzp", "out"), model="DSCH")])
        ev0 = Evaluation(scalar=3.0)
        best, ev, tried = refine(c, ev0, fake_eval, budget=10, rng=random.Random(1))
        self.assertIs(best, c)
        self.assertIs(ev, ev0)
        self.assertEqual(tried, [])

    def test_phase_is_additive(self):
        c = Circuit("s", [Component("L1", "L", ("pzp", "n1"), value=1e-3),
                          Component("S1", "S", ("n1", "pzn"), ctrl="G1"),
                          Component("G1", "SYNC", (), ton=3e-5, phase=0.0, edges="both")])

        def ev_phase(x):
            return Evaluation(scalar=-abs(get_param(x, "G1", "phase") - 0.1))
        best, _, _ = refine(c, ev_phase(c), ev_phase, budget=60, rng=random.Random(3))
        self.assertAlmostEqual(get_param(best, "G1", "phase"), 0.1, delta=0.01)


if __name__ == "__main__":
    unittest.main()
