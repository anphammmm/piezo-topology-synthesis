"""The benchmark of specifications: selection, physics sanity, and that nothing downstream keeps P1's numbers."""
import json
import math
import tempfile
import unittest
from pathlib import Path

from piezo_synth import spec

VD = 0.3   # a Schottky drop at microamps, for the open-circuit voltage arguments below


def voc(c):
    return c.ip / (2 * math.pi * c.freq * c.cp)


def p_star(c):
    return c.ip ** 2 / (4 * math.pi ** 2 * c.freq * c.cp)


class RegistryTest(unittest.TestCase):
    def tearDown(self):
        spec.use("P1")

    def test_registry_and_default(self):
        self.assertEqual(list(spec.SPECS), ["P1", "P2", "P3", "P4", "P5"])
        self.assertEqual(spec.ACTIVE, "P1")
        self.assertEqual(spec.vmin(), 1.8)

    def test_use_swaps_in_place_and_restores(self):
        conds, crits, screen = spec.CONDITIONS, spec.CRITERIA, spec.SCREEN
        spec.use("P2")
        self.assertIs(spec.CONDITIONS, conds)          # modules that imported the objects see the change
        self.assertIs(spec.CRITERIA, crits)
        self.assertIs(spec.SCREEN, screen)
        self.assertEqual(spec.ACTIVE, "P2")
        self.assertEqual(spec.vmin(), 4.5)
        self.assertEqual(spec.SCREEN["vstore"], 4.5)
        self.assertEqual(spec.spec_dict()["name"], "P2")
        spec.use("P1")
        self.assertEqual(spec.vmin(), 1.8)
        self.assertEqual(spec.condition("S4").ip, 30e-6)

    def test_using_context(self):
        with spec.using("P3"):
            self.assertEqual(spec.ACTIVE, "P3")
        self.assertEqual(spec.ACTIVE, "P1")

    def test_unknown_spec(self):
        with self.assertRaises(KeyError):
            spec.use("P9")

    def test_every_spec_is_well_formed(self):
        for name in spec.SPECS:
            with spec.using(name):
                ids = [c.id for c in spec.search_conditions()]
                self.assertEqual(ids, ["S1", "S2", "S3", "S4", "S5", "S6"], name)
                self.assertGreaterEqual(len(spec.heldout_conditions()), 3, name)
                self.assertEqual(tuple(spec.SCREEN["conditions"]), ("S2", "S4", "S6"), name)
                self.assertEqual([c.id for c in spec.CRITERIA],
                                 ["vout_min", "vout_max", "ripple", "startup", "settled"], name)
                self.assertLess(spec.vmin(), spec.vmax(), name)
                for c in spec.CONDITIONS:
                    lo, hi = spec.LIMITS["R"]
                    self.assertTrue(lo <= c.rl <= hi, (name, c.id))
                    self.assertGreater(p_star(c), spec.vmin() ** 2 / c.rl, (name, c.id, "need above P*"))
                self.assertTrue(spec.SPECS[name].title and spec.SPECS[name].hardness, name)


class PhysicsTest(unittest.TestCase):
    """Each spec's intended difficulty, checked from the source model alone."""

    def tearDown(self):
        spec.use("P1")

    def test_p2_bridge_cannot_reach_window_on_most_conditions(self):
        with spec.using("P2"):
            dead = [c.id for c in spec.search_conditions() if voc(c) < spec.vmin() + 2 * VD]
            self.assertGreaterEqual(len(dead), 4, dead)
            self.assertGreater(max(voc(c) for c in spec.CONDITIONS), spec.vmax())   # a clamp is needed

    def test_p3_below_one_bridge_and_controller_too_costly(self):
        with spec.using("P3"):
            for c in spec.search_conditions():
                if c.id != "S3":
                    self.assertLess(voc(c), spec.vmin() / 2, c.id)
                # one SYNC controller's supply current costs more than the load needs
                self.assertGreater(spec.CTRL_SINK_A * spec.vmin(), spec.vmin() ** 2 / c.rl, c.id)
            self.assertGreater(voc(spec.condition("S3")), 2.0)

    def test_p4_wide_frequency_and_hot_heavy_in_search(self):
        with spec.using("P4"):
            fs = [c.freq for c in spec.search_conditions()]
            self.assertLessEqual(min(fs), 50)
            self.assertGreaterEqual(max(fs), 200)
            self.assertTrue(any(c.temp >= 85 for c in spec.search_conditions()))
            cps = [c.cp for c in spec.search_conditions()]
            self.assertGreaterEqual(max(cps) / min(cps), 1.8)

    def test_p5_tighter_ripple_and_startup(self):
        with spec.using("P5"):
            lim = {c.id: c.limit for c in spec.CRITERIA}
            self.assertLessEqual(lim["ripple"], 0.02)
            self.assertLessEqual(lim["startup"], 0.15)


class DownstreamTest(unittest.TestCase):
    def tearDown(self):
        spec.use("P1")

    def test_netlist_startup_threshold_follows_vmin(self):
        from piezo_synth.netlist import build_netlist, reference_circuit
        with spec.using("P2"):
            n = build_netlist(reference_circuit(), spec.condition("S1"))
            self.assertIn("V(out)=4.5 RISE=1", n)

    def test_screen_bench_holds_vmin(self):
        from piezo_synth.netlist import build_screen_netlist, reference_circuit
        with spec.using("P2"):
            self.assertIn("Vst vsn 0 4.5", build_screen_netlist(reference_circuit(), spec.condition("S2")))

    def test_prompt_states_active_numbers(self):
        from piezo_synth.evaluate import evaluate
        from piezo_synth.prompts import system_prompt
        from piezo_synth.sim import SimResult
        with spec.using("P2"):
            conds = spec.search_conditions()
            ev = evaluate({c.id: SimResult(True, {"vavg": 1.0, "vmax": 1.2, "vpp": 0.01, "tup": None,
                                                  "vavg_prev": 1.0, "pload": 1e-7, "pext": 1e-7}, "", 1, "f")
                           for c in conds}, conds)
            p = system_prompt(ev)
            self.assertIn("V(out) reaches 4.5 V", p)
            self.assertIn("out fixed at 4.5 V", p)
            self.assertNotIn("about 3.2 V at nominal", p)

    def test_diagnostics_use_active_window(self):
        from piezo_synth.diagnostics import hints
        from piezo_synth.evaluate import evaluate
        from piezo_synth.sim import SimResult
        with spec.using("P2"):
            conds = spec.search_conditions()
            ev = evaluate({c.id: SimResult(True, {"vavg": 3.9, "vmax": 4.0, "vpp": 0.01, "tup": None,
                                                  "vavg_prev": 3.9, "pload": 1e-7, "pext": 1e-7}, "", 1, "f")
                           for c in conds}, conds)
            text = " ".join(h.text for h in hints(ev))
            self.assertIn("below 4.5 V", text)
            self.assertNotIn("pinned", " ".join(h.code for h in hints(ev)))

    def test_spec_witnesses_are_valid(self):
        from piezo_synth.circuit import validate
        from piezo_synth.netlist import spec_witness, witness_circuit
        for name in spec.SPECS:
            with spec.using(name):
                for c in (spec_witness(), witness_circuit()):
                    self.assertEqual(validate(c), [], (name, c.name))

    def test_fake_run_records_spec(self):
        from piezo_synth import run as run_mod
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "r"
            cfg = Path(d) / "c.json"
            cfg.write_text(json.dumps({"max_rounds": 2, "mc_samples": 0, "size_budget": 4, "size_lambda": 2}))
            run_mod.main(["--fake", "--spec", "P3", "--config", str(cfg), "--out", str(out)])
            self.assertEqual(json.loads((out / "spec.json").read_text())["name"], "P3")
            self.assertEqual(json.loads((out / "run_meta.json").read_text())["spec"], "P3")
        self.assertEqual(spec.ACTIVE, "P1")


if __name__ == "__main__":
    unittest.main()
