import unittest

from piezo_synth import spec
from piezo_synth.circuit import parse_circuit, validate
from piezo_synth.netlist import (MEAS_NAMES, build_netlist, reference_circuit, sync_timing,
                                 witness_circuit)
from tests.test_circuit import EXAMPLE, rename


class NetlistTest(unittest.TestCase):
    def test_reference_and_witness_are_valid(self):
        self.assertEqual(validate(reference_circuit()), [])
        self.assertEqual(validate(witness_circuit()), [])

    def test_reference_netlist_has_bench_and_meas(self):
        n = build_netlist(reference_circuit(), spec.condition("S1"))
        for s in ["Ipz pzn pzp SINE(0 5e-05 100)", "Cpz pzp pzn 2.5e-08", "Rpz pzp pzn 2e+07",
                  "RL out 0 330000", ".temp 27", ".tran 0 0.8 0 2e-06",
                  ".meas TRAN tup FIND time WHEN V(out)=1.8 RISE=1", ".model DSCH", ".save V(out)",
                  ".meas TRAN pload AVG V(out)*V(out)/330000 FROM=0.7 TO=0.8", ".end"]:
            self.assertIn(s, n)
        for m in MEAS_NAMES:
            self.assertIn(f".meas TRAN {m} ", n)
        self.assertNotIn("Ictl", n)

    def test_inductor_gets_series_resistance(self):
        self.assertIn("Rser=25.5", build_netlist(witness_circuit(), spec.condition("S1")))

    def test_sync_source_and_sink(self):
        n = build_netlist(witness_circuit(), spec.condition("S5"))
        self.assertIn("Ictl1 out 0 5e-07", n)
        self.assertIn("VG1 G1_g 0 PULSE(0 1 0 100n 100n 3.4e-05 0.00625)", n)
        self.assertRegex(n, r"\nS1 \S+ \S+ G1_g 0 SWI\n")

    def test_sync_timing(self):
        t0, per = sync_timing(1e-5, 0.0, "pos", 100)
        self.assertAlmostEqual(t0, 0.005)
        self.assertAlmostEqual(per, 0.01)
        t0, per = sync_timing(1e-5, -0.1, "both", 100)
        self.assertAlmostEqual(per, 0.005)
        self.assertAlmostEqual(t0, 0.004)          # -1 ms wrapped into [0, 5 ms)
        self.assertAlmostEqual(sync_timing(1e-5, 0.1, "neg", 100)[0], 0.001)

    def test_bleed_on_internal_and_piezo_nodes(self):
        n = build_netlist(witness_circuit(), spec.condition("S1"))
        self.assertIn("Rbleed_n1 n1 0 1G", n)
        self.assertNotIn("Rbleed_out", n)
        self.assertIn("Rbleed_pzp pzp 0 1G", n)
        self.assertIn("Rbleed_pzn pzn 0 1G", n)

    def test_renamed_circuits_same_netlist(self):
        a = parse_circuit(EXAMPLE)
        b = parse_circuit(rename(EXAMPLE, {"n1": "mid", "D1": "Dx", "G1": "Gq"}))
        c = spec.condition("S2")
        self.assertEqual(build_netlist(a, c), build_netlist(b, c))

    def test_save_all_and_temperature(self):
        n = build_netlist(reference_circuit(), spec.condition("H3"), save_all=True)
        self.assertNotIn(".save", n)
        self.assertIn(".temp -20", n)


if __name__ == "__main__":
    unittest.main()
