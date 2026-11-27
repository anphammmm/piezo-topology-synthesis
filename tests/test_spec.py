import json
import unittest

from piezo_synth import spec


class SpecTest(unittest.TestCase):
    def test_split_counts(self):
        self.assertEqual([c.id for c in spec.search_conditions()], ["S1", "S2", "S3", "S4", "S5", "S6"])
        self.assertEqual([c.id for c in spec.heldout_conditions()], ["H1", "H2", "H3", "H4"])

    def test_pinned_values(self):
        s4 = spec.condition("S4")
        self.assertEqual((s4.ip, s4.rl, s4.freq), (30e-6, 1e6, 100))
        h2 = spec.condition("H2")
        self.assertEqual((h2.cp, h2.freq), (21.25e-9, 120))
        self.assertEqual({c.id: (c.op, c.limit) for c in spec.CRITERIA}["startup"], ("<=", 0.4))
        self.assertTrue(all(c.rp == 20e6 for c in spec.CONDITIONS))

    def test_spec_dict_is_json(self):
        d = json.loads(json.dumps(spec.spec_dict()))
        self.assertEqual(len(d["conditions"]), 10)
        self.assertEqual(len(d["criteria"]), 5)
        self.assertEqual(d["limits"]["L"], [1e-5, 1e-2])
