import math
import random
import re
import tempfile
import unittest
from pathlib import Path

from piezo_synth import spec
from piezo_synth.circuit import get_param, with_param
from piezo_synth.netlist import build_screen_netlist, reference_circuit, witness_circuit
from piezo_synth.screen import p_fbr_ideal, physics_presets, screen
from piezo_synth.sim import Simulator
from tests.fakes import FakeBackend


def isn_for(p_net):
    """Sense-resistor voltage that the screen converts back into p_net watts."""
    return p_net * spec.SCREEN["rsense"] / spec.SCREEN["vstore"]


def need(cid):
    c = spec.condition(cid)
    return spec.SCREEN["vstore"] ** 2 / c.rl


class ScreenNetlistTest(unittest.TestCase):
    def test_screen_bench_holds_out_at_vstore_and_is_short(self):
        cond = spec.condition("S4")
        text = build_screen_netlist(witness_circuit(), cond)
        self.assertNotRegex(text, r"(?m)^RL ")
        self.assertRegex(text, r"(?m)^Rsense out vsn 100$")
        self.assertRegex(text, r"(?m)^Vst vsn 0 1\.8$")
        tstop = spec.SCREEN["cycles"] / cond.freq
        self.assertIn(f".tran 0 {tstop:.6g} 0 2e-06", text)
        self.assertRegex(text, r"(?m)^\.meas TRAN isn AVG V\(out,vsn\) FROM=0\.06 TO=0\.1$")
        self.assertRegex(text, r"(?m)^Ictl1 out 0 5e-07$")


class ScreenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def sim(self, fn):
        self.backend = FakeBackend(fn)
        return Simulator(self.backend, Path(self.tmp.name), workers=4)

    def test_fbr_ideal_power(self):
        c = spec.condition("S1")
        self.assertAlmostEqual(p_fbr_ideal(c), c.ip ** 2 / (4 * math.pi ** 2 * c.freq * c.cp))

    def test_passes_when_every_screen_condition_has_enough_power(self):
        def fn(text):
            rl_cid = re.search(r"condition (S\d)", text).group(1)
            return {"isn": isn_for(need(rl_cid) * 1.2), "vout": 1.81}
        r = screen(witness_circuit(), self.sim(fn), random.Random(1), "w")
        self.assertTrue(r.passed)
        self.assertEqual(sorted(r.ratio), sorted(spec.SCREEN["conditions"]))
        for cid in r.ratio:
            self.assertAlmostEqual(r.ratio[cid], 1.2, places=6)
            self.assertAlmostEqual(r.gain[cid], need(cid) * 1.2 / p_fbr_ideal(spec.condition(cid)), places=12)

    def test_fails_on_worst_condition(self):
        def fn(text):
            cid = re.search(r"condition (S\d)", text).group(1)
            return {"isn": isn_for(need(cid) * (0.2 if cid == "S4" else 2.0)), "vout": 1.8}
        r = screen(reference_circuit(), self.sim(fn), random.Random(1), "ref")
        self.assertFalse(r.passed)
        self.assertAlmostEqual(r.worst_ratio, 0.2, places=6)

    def test_failed_simulation_fails_the_screen(self):
        r = screen(reference_circuit(), self.sim(lambda text: None), random.Random(1), "ref")
        self.assertFalse(r.passed)
        self.assertTrue(r.sim_failed)

    def test_best_preset_is_returned(self):
        target = math.pi * math.sqrt(4.7e-3 * spec.condition("S1").cp)

        def fn(text):
            ton = float(re.search(r"PULSE\(0 1 \S+ 100n 100n (\S+) ", text).group(1))
            cid = re.search(r"condition (S\d)", text).group(1)
            good = abs(ton - target) / target < 0.01
            return {"isn": isn_for(need(cid) * (1.5 if good else 0.3)), "vout": 1.8}
        w = with_param(witness_circuit(), "G1", "ton", 10e-6)
        r = screen(w, self.sim(fn), random.Random(1), "w")
        self.assertTrue(r.passed)
        self.assertAlmostEqual(get_param(r.circuit, "G1", "ton"), target, places=9)
        self.assertGreaterEqual(r.n_presets, 2)

    def test_physics_presets_use_lc_resonance(self):
        ps = physics_presets(witness_circuit())
        tons = sorted(get_param(p, "G1", "ton") for p in ps)
        res = math.pi * math.sqrt(4.7e-3 * spec.condition("S1").cp)
        self.assertAlmostEqual(tons[-1], res, places=12)
        self.assertAlmostEqual(tons[0], res / 2, places=12)
        self.assertEqual(physics_presets(reference_circuit()), [])


if __name__ == "__main__":
    unittest.main()
