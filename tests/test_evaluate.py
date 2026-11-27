import unittest

from piezo_synth import spec
from piezo_synth.evaluate import diagnose, evaluate, is_better
from piezo_synth.sim import SimResult

S1, S2 = spec.condition("S1"), spec.condition("S2")
GOOD = dict(vavg=2.5, vavg_prev=2.49, vpp=0.02, vmax=2.6, tup=0.2, pload=1e-5, pext=2e-5)


def ok(**m):
    return SimResult(True, m, "", 1.0, "f")


class EvaluateTest(unittest.TestCase):
    def test_all_pass(self):
        ev = evaluate({"S1": ok(**GOOD)}, [S1])
        self.assertTrue(ev.all_pass)
        self.assertEqual((ev.cond_pass, ev.checks_pass), (1, 5))
        self.assertAlmostEqual(ev.meas["S1"]["dv"], 0.01)

    def test_missing_measurement_fails_check(self):
        m = dict(GOOD)
        del m["tup"]
        m["vavg"] = 1.2
        ev = evaluate({"S1": ok(**m)}, [S1])
        c = {x.criterion: x for x in ev.checks}["startup"]
        self.assertIsNone(c.measured)
        self.assertFalse(c.passed)
        self.assertEqual(c.margin, -1)
        self.assertFalse(ev.all_pass)

    def test_nan_measurement_fails(self):
        m = dict(GOOD, vpp=float("nan"))
        c = {x.criterion: x for x in evaluate({"S1": ok(**m)}, [S1]).checks}["ripple"]
        self.assertFalse(c.passed)

    def test_failed_sim_fails_all_checks_of_that_condition(self):
        ev = evaluate({"S1": ok(**GOOD), "S2": SimResult(False, {}, "boom", 1, "f")}, [S1, S2])
        s2 = [c for c in ev.checks if c.condition == "S2"]
        self.assertEqual(len(s2), 5)
        self.assertTrue(all(not c.passed and c.margin == -1 for c in s2))
        self.assertEqual(ev.cond_pass, 1)
        self.assertEqual(ev.sim_error["S2"], "boom")

    def test_margin_values(self):
        ev = evaluate({"S1": ok(**dict(GOOD, vavg=1.71, vavg_prev=1.71))}, [S1])
        c = {x.criterion: x for x in ev.checks}["vout_min"]
        self.assertAlmostEqual(c.margin, -0.05)
        c = {x.criterion: x for x in ev.checks}["vout_max"]
        self.assertAlmostEqual(c.margin, (3.6 - 2.6) / 3.6)

    def test_scalar_orders_designs(self):
        # passes S1 fully, fails S2 badly  vs  fails both narrowly
        a = evaluate({"S1": ok(**GOOD), "S2": ok(**dict(GOOD, vavg=0.5))}, [S1, S2])
        b = evaluate({"S1": ok(**dict(GOOD, vpp=0.051)), "S2": ok(**dict(GOOD, vpp=0.051))}, [S1, S2])
        self.assertGreater(a.scalar, b.scalar)
        self.assertTrue(is_better(a, b, 9, 5))
        self.assertTrue(is_better(a, None, 9, 0))
        self.assertTrue(is_better(a, a, 4, 5))      # tie -> fewer components
        self.assertFalse(is_better(a, a, 5, 5))

    def test_diagnose_worst_first(self):
        ev = evaluate({"S1": ok(**dict(GOOD, vavg=1.0, vavg_prev=1.0, vpp=0.06)), "S2": SimResult(False, {}, "x" * 500, 1, "f")},
                      [S1, S2])
        text = diagnose(ev)
        lines = text.splitlines()
        self.assertTrue(lines[0].startswith("S1 vout_min"))
        self.assertIn("needs >= 1.8 V", lines[0])
        self.assertIn("S2: simulation failed", text)
        self.assertLess(max(len(l) for l in lines), 300)


if __name__ == "__main__":
    unittest.main()
