import copy
import unittest

from piezo_synth.circuit import (CircuitError, design_hash, get_param, numeric_params, parse_circuit,
                                 to_dict, topology_hash, with_param, canonical, describe)

EXAMPLE = {
    "move": "new_topology", "name": "p-SSHI + bridge", "rationale": "x", "done": False,
    "components": [
        {"id": "D1", "type": "D", "nodes": ["pzp", "out"], "model": "DSCH"},
        {"id": "D2", "type": "D", "nodes": ["pzn", "out"], "model": "DSCH"},
        {"id": "D3", "type": "D", "nodes": ["0", "pzp"], "model": "DSCH"},
        {"id": "D4", "type": "D", "nodes": ["0", "pzn"], "model": "DSCH"},
        {"id": "C1", "type": "C", "nodes": ["out", "0"], "value": 2.2e-6},
        {"id": "L1", "type": "L", "nodes": ["pzp", "n1"], "value": 4.7e-3},
        {"id": "S1", "type": "S", "nodes": ["n1", "pzn"], "ctrl": "G1"},
        {"id": "G1", "type": "SYNC", "ton": 3.4e-5, "phase": 0.0, "edges": "both"},
    ],
}


def rename(obj, mapping):
    o = copy.deepcopy(obj)
    for comp in o["components"]:
        comp["id"] = mapping.get(comp["id"], comp["id"])
        if "nodes" in comp:
            comp["nodes"] = [mapping.get(n, n) for n in comp["nodes"]]
        if "ctrl" in comp:
            comp["ctrl"] = mapping.get(comp["ctrl"], comp["ctrl"])
    o["components"].reverse()
    return o


def problems_of(obj):
    try:
        parse_circuit(obj)
    except CircuitError as e:
        return " | ".join(e.problems)
    return ""


class CircuitTest(unittest.TestCase):
    def test_valid_example_parses(self):
        c = parse_circuit(EXAMPLE)
        self.assertEqual(len(c.components), 8)
        self.assertEqual(c.name, "p-SSHI + bridge")

    def test_all_problems_reported(self):
        bad = {"move": "resize", "components": [
            {"id": "R1", "type": "R", "nodes": ["pzp"], "value": 0.1},
            {"id": "X1", "type": "Q", "nodes": ["a", "b"]}]}
        msgs = problems_of(bad)
        self.assertIn("R1", msgs)
        self.assertIn("X1", msgs)
        self.assertIn("out", msgs)

    def test_dangling_node_rejected(self):
        o = copy.deepcopy(EXAMPLE)
        o["components"].append({"id": "R9", "type": "R", "nodes": ["out", "n9"], "value": 1e3})
        self.assertIn("n9", problems_of(o))

    def test_sync_unused_rejected(self):
        o = copy.deepcopy(EXAMPLE)
        o["components"] = [c for c in o["components"] if c["id"] not in ("S1", "L1")]
        self.assertIn("G1", problems_of(o))

    def test_bad_move_and_bounds(self):
        o = copy.deepcopy(EXAMPLE)
        o["move"] = "teleport"
        o["components"][4]["value"] = 1.0
        msgs = problems_of(o)
        self.assertIn("move", msgs)
        self.assertIn("C1", msgs)

    def test_out_disconnected_from_piezo(self):
        o = {"move": "new_topology", "components": [
            {"id": "C1", "type": "C", "nodes": ["out", "0"], "value": 1e-6},
            {"id": "R1", "type": "R", "nodes": ["pzp", "pzn"], "value": 1e3}]}
        self.assertIn("connected", problems_of(o))

    def test_renamed_circuit_same_hash(self):
        a = parse_circuit(EXAMPLE)
        b = parse_circuit(rename(EXAMPLE, {"n1": "mid", "D1": "Dx", "G1": "Gq", "S1": "Sw"}))
        self.assertEqual(topology_hash(a), topology_hash(b))
        self.assertEqual(design_hash(a), design_hash(b))

    def test_value_change_keeps_topology_hash(self):
        a = parse_circuit(EXAMPLE)
        b = with_param(a, "C1", "value", 4.7e-6)
        self.assertEqual(topology_hash(a), topology_hash(b))
        self.assertNotEqual(design_hash(a), design_hash(b))

    def test_rewire_changes_topology_hash(self):
        o = copy.deepcopy(EXAMPLE)
        o["components"][6]["nodes"] = ["n1", "out"]
        self.assertNotEqual(topology_hash(parse_circuit(EXAMPLE)), topology_hash(parse_circuit(o)))

    def test_with_param_clamps(self):
        a = parse_circuit(EXAMPLE)
        self.assertEqual(get_param(with_param(a, "L1", "value", 1.0), "L1", "value"), 1e-2)
        self.assertEqual(get_param(a, "L1", "value"), 4.7e-3)   # original untouched

    def test_numeric_params(self):
        p = numeric_params(parse_circuit(EXAMPLE))
        self.assertIn(("C1", "value"), p)
        self.assertIn(("G1", "ton"), p)
        self.assertIn(("G1", "phase"), p)
        self.assertNotIn(("D1", "value"), p)

    def test_roundtrip(self):
        a = parse_circuit(EXAMPLE)
        self.assertEqual(design_hash(parse_circuit(to_dict(a))), design_hash(a))

    def test_canonical_names(self):
        c = canonical(parse_circuit(rename(EXAMPLE, {"n1": "zz"})))
        nodes = {n for comp in c.components for n in comp.nodes}
        self.assertIn("n1", nodes)
        self.assertNotIn("zz", nodes)
        self.assertIn("SYNC", describe(c))


if __name__ == "__main__":
    unittest.main()


class ParseValueTest(unittest.TestCase):
    def test_spice_suffixes(self):
        from piezo_synth.circuit import parse_value
        self.assertAlmostEqual(parse_value("2.2u"), 2.2e-6)
        self.assertAlmostEqual(parse_value("4.7meg"), 4.7e6)
        self.assertAlmostEqual(parse_value("10k"), 1e4)
        self.assertAlmostEqual(parse_value("4.7mH"), 4.7e-3)
        self.assertIsNone(parse_value("lots"))
        self.assertIsNone(parse_value(True))


class DiodeOrientationTest(unittest.TestCase):
    def test_forward_diode_from_out_to_ground_rejected(self):
        bad = copy.deepcopy(EXAMPLE)
        bad["components"].append({"id": "DZ1", "type": "D", "nodes": ["out", "0"], "model": "DZ33"})
        p = problems_of(bad)
        self.assertIn("DZ1", p)
        self.assertIn('["0", "out"]', p)

    def test_zener_clamp_with_cathode_on_out_accepted(self):
        ok = copy.deepcopy(EXAMPLE)
        ok["components"].append({"id": "DZ1", "type": "D", "nodes": ["0", "out"], "model": "DZ33"})
        self.assertEqual(problems_of(ok), "")
