import unittest

from piezo_synth import spec
from piezo_synth.diagnostics import codes, hints, repeated
from piezo_synth.evaluate import evaluate
from piezo_synth.screen import ScreenResult
from piezo_synth.sim import SimResult

CONDS = spec.search_conditions()
GOOD = dict(vavg=2.5, vavg_prev=2.49, vpp=0.02, vmax=2.6, tup=0.2, pload=1e-5, pext=2e-5)


def ev_with(per_cond):
    return evaluate({c.id: (SimResult(True, per_cond(c.id), "", 1, "f") if per_cond(c.id) is not None
                            else SimResult(False, {}, "singular matrix", 1, "f")) for c in CONDS}, CONDS)


class HintTest(unittest.TestCase):
    def test_pinned_output_points_at_diode_orientation(self):
        hs = hints(ev_with(lambda cid: dict(GOOD, vavg=0.66, vavg_prev=0.66, vmax=0.67, tup=None)))
        self.assertEqual(codes(hs), {"pinned"})
        self.assertIn("orientation", hs[0].text)

    def test_overvoltage_and_underpower_named_per_condition(self):
        def m(cid):
            if cid == "S3":
                return dict(GOOD, vavg=5.7, vavg_prev=5.7, vmax=5.72)
            if cid == "S4":
                return dict(GOOD, vavg=1.5, vavg_prev=1.5, vmax=1.52, tup=None)
            return GOOD
        hs = hints(ev_with(m))
        self.assertEqual(codes(hs), {"overvoltage", "underpower"})
        text = " ".join(h.text for h in hs)
        self.assertIn("S3", text)
        self.assertIn("S4 (weak excitation) at 1.50 V", text)

    def test_slow_start_drift_ripple(self):
        hs = hints(ev_with(lambda cid: dict(GOOD, tup=0.55, vavg_prev=2.4, vpp=0.08)))
        self.assertEqual(codes(hs), {"slow_start", "not_settled", "ripple"})

    def test_simulation_failure(self):
        hs = hints(ev_with(lambda cid: None if cid == "S2" else GOOD))
        self.assertIn("sim_failed", codes(hs))

    def test_all_good_gives_nothing(self):
        self.assertEqual(hints(ev_with(lambda cid: GOOD)), [])

    def test_screen_shortfall(self):
        scr = ScreenResult(False, None, 0.3, ratio={"S2": 1.4, "S4": 0.3}, p_net={"S2": 3e-5, "S4": 1e-6},
                           p_req={"S2": 2.16e-5, "S4": 3.24e-6})
        hs = hints(screen=scr)
        self.assertEqual(codes(hs), {"underpower"})
        self.assertIn("30 % of the load's need on S4", hs[0].text)

    def test_repeated(self):
        self.assertEqual(repeated([{"pinned"}, {"pinned", "ripple"}, {"pinned"}]), ["pinned"])
        self.assertEqual(repeated([{"pinned"}, {"ripple"}, {"pinned"}]), [])
        self.assertEqual(repeated([{"pinned"}, {"pinned"}]), [])


if __name__ == "__main__":
    unittest.main()
