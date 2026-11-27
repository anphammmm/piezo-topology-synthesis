import unittest

from piezo_synth import spec
from piezo_synth.circuit import describe
from piezo_synth.evaluate import diagnose, evaluate
from piezo_synth.netlist import reference_circuit
from piezo_synth.prompts import (condition_table, iteration_prompt, repair_messages, required_move,
                                 system_prompt)
from piezo_synth.sim import SimResult

GOOD = dict(vavg=2.5, vavg_prev=2.49, vpp=0.02, vmax=2.6, tup=0.2, pload=1e-5, pext=2e-5)
REF_EV = evaluate({c.id: SimResult(True, dict(GOOD, vavg=1.2), "", 1, "f") for c in spec.search_conditions()},
                  spec.search_conditions())


def entry(i, **extra):
    d = {"id": f"c{i:04d}", "name": f"design {i}", "topo_hash": "abc123def456", "scalar": 12.5,
         "cond_pass": 1, "circuit_text": describe(reference_circuit()),
         "diagnosis": diagnose(REF_EV), "table": condition_table(REF_EV, spec.search_conditions())}
    d.update(extra)
    return d


class PromptTest(unittest.TestCase):
    def test_system_prompt_has_spec_and_reference(self):
        p = system_prompt(REF_EV)
        for s in ["S1", "S6", "1.8", "3.6", "DZ33", "DSCH", "SYNC", "\"components\"", "FBR", "pzp", "out",
                  "new_topology", "connectivity"]:
            self.assertIn(s, p)

    def test_system_prompt_explains_diode_orientation(self):
        p = system_prompt(REF_EV)
        self.assertIn('["0", "out"]', p)        # zener clamp: cathode on out
        self.assertIn('["0", "pzp"]', p)        # bridge return diode: anode on ground
        self.assertIn("anode", p)

    def test_system_prompt_describes_screen_sizing_and_multi_reply(self):
        p = system_prompt(REF_EV, per_round=3, screen=True, size_budget=48)
        self.assertIn('"proposals"', p)
        self.assertIn("up to 3", p)
        self.assertIn("fixed at 1.8 V", p)
        self.assertIn("48", p)
        p = system_prompt(REF_EV, per_round=1, screen=False, size_budget=48)
        self.assertNotIn("fixed at 1.8 V", p)
        self.assertIn("exactly 1", p)

    def test_iteration_prompt_reports_every_proposal_of_last_round(self):
        last = [
            {"kind": "evaluated", **entry(5), "hints": ["the output settles below 1.8 V on S4"],
             "screen": "S4: 2 uW of 3 uW needed (66 %)"},
            {"kind": "screen_failed", "name": "weak one", "topo_hash": "aaa111bbb222",
             "screen": "S2: 1 uW of 21.6 uW needed (5 %)", "hints": ["net power covers only 5 %"],
             "circuit_text": "D1 D pzp out DSCH"},
            {"kind": "duplicate", "name": "again", "id": "c0003"},
            {"kind": "invalid", "name": "broken", "invalid_problems": ["R1: value 0 outside"]},
        ]
        p = iteration_prompt(3, 12, [entry(1)], last, [], None)
        for s_ in ("Round 3 of 12", "the output settles below 1.8 V on S4", "weak one", "not tuned",
                   "S2: 1 uW of 21.6 uW", "c0003", "R1: value 0 outside", "66 %"):
            self.assertIn(s_, p)

    def test_repeated_problem_is_flagged(self):
        p = iteration_prompt(4, 12, [], [], [], None, repeated=["pinned"])
        self.assertIn("REPEATED", p)
        self.assertIn("pinned", p.lower())

    def test_heldout_never_in_prompts(self):
        last = entry(3, duplicate=False, invalid_problems=[], refined_from=None)
        p = system_prompt(REF_EV) + iteration_prompt(3, 16, [entry(1), entry(2)], last,
                                                     [{"topo_hash": "abc", "name": "x", "best_scalar": 1.0}], None)
        for h in spec.heldout_conditions():
            self.assertNotIn(h.id, p)
            self.assertNotIn(h.label, p)
        self.assertNotIn("120 Hz", p)
        self.assertNotIn("-20", p)
        self.assertNotIn("held", p.lower())

    def test_required_move(self):
        self.assertTrue(required_move(["new_topology", "resize", "resize", "resize"]))
        self.assertIsNone(required_move(["resize", "modify_topology", "resize"]))
        self.assertIsNone(required_move([]))

    def test_iteration_prompt_mentions_duplicate_and_invalid(self):
        p = iteration_prompt(4, 16, [entry(1)], entry(2, duplicate=True, invalid_problems=[], refined_from=None),
                             [], "new_topology or modify_topology")
        self.assertIn("duplicate", p.lower())
        self.assertIn("MUST", p)
        self.assertIn("Round 4 of 16", p)
        p = iteration_prompt(4, 16, [entry(1)], {"duplicate": False, "invalid_problems": ["R1: bad"],
                                                 "name": "x", "refined_from": None}, [], None)
        self.assertIn("R1: bad", p)

    def test_iteration_prompt_with_no_history(self):
        p = iteration_prompt(1, 16, [], None, [], None)
        self.assertIn("first", p.lower())

    def test_condition_table(self):
        t = condition_table(REF_EV, spec.search_conditions())
        self.assertIn("S4", t)
        self.assertIn("FAIL", t)

    def test_repair_messages(self):
        m = repair_messages("sys", "user", "bad answer", ["C1: value 1 outside"])
        self.assertEqual([x["role"] for x in m], ["system", "user", "assistant", "user"])
        self.assertIn("C1: value 1 outside", m[-1]["content"])


if __name__ == "__main__":
    unittest.main()
