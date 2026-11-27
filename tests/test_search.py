import copy
import re
import json
import tempfile
import unittest
from pathlib import Path

from piezo_synth import spec
from piezo_synth.circuit import to_dict
from piezo_synth.llm import LLMReply
from piezo_synth.netlist import reference_circuit, witness_circuit
from piezo_synth.records import RunRecorder
from piezo_synth.search import SearchConfig, run_search
from piezo_synth.sim import Simulator
from tests.fakes import FakeBackend, FakeLLM

GOOD = dict(vavg=2.5, vavg_prev=2.49, vpp=0.02, vmax=2.6, tup=0.2, pload=1e-5, pext=2e-5)
POOR = dict(vavg=1.2, vavg_prev=1.19, vpp=0.03, vmax=1.3, pload=1e-6, pext=2e-6)   # no tup


def uses(text, model):
    return re.search(rf"^[DS]\w* .* {model}$", text, re.M) is not None


def physics(text):
    if uses(text, "DSI"):
        return None                         # this design does not simulate
    if uses(text, "DZ33") and uses(text, "SWI"):
        return GOOD
    if uses(text, "SWI"):
        return dict(GOOD, vmax=4.0)         # better: only overvoltage fails
    return POOR


WITNESS = dict(to_dict(witness_circuit()), move="new_topology", name="sshi + clamp")
SSHI_NO_CLAMP = copy.deepcopy(WITNESS)
SSHI_NO_CLAMP["components"] = [c for c in SSHI_NO_CLAMP["components"] if c.get("model") != "DZ33"]
SSHI_NO_CLAMP["name"] = "sshi"
BROKEN = copy.deepcopy(SSHI_NO_CLAMP)
for comp in BROKEN["components"]:
    if comp.get("model") == "DSCH":
        comp["model"] = "DSI"


def renamed(obj, old, new):
    o = copy.deepcopy(obj)
    for comp in o["components"]:
        if "nodes" in comp:
            comp["nodes"] = [new if n == old else n for n in comp["nodes"]]
    return o


class SearchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self.backend = FakeBackend(physics)
        self.sim = Simulator(self.backend, self.out, workers=4)
        self.rec = RunRecorder(self.out, quiet=True)

    def tearDown(self):
        self.tmp.cleanup()

    def cfg(self, **kw):
        base = dict(max_proposals=6, min_proposals=1, refine_budget=0, refine_min=0, heartbeat_s=0.01)
        base.update(kw)
        return SearchConfig(**base)

    def events(self):
        return [json.loads(l) for l in (self.out / "events.jsonl").read_text().splitlines()]

    def test_search_meets_spec_and_runs_heldout(self):
        out = run_search(self.cfg(), FakeLLM([json.dumps(WITNESS)]), self.sim, self.rec)
        self.assertEqual(out.stop_reason, "search_spec_met")
        self.assertTrue(out.met_search)
        self.assertTrue(out.met_all)
        self.assertEqual({c.condition for c in out.heldout_selected.checks}, {"H1", "H2", "H3", "H4"})
        self.assertEqual({c.condition for c in out.heldout_reference.checks}, {"H1", "H2", "H3", "H4"})
        self.assertTrue((self.out / "selected" / "circuit.json").exists())
        self.assertTrue((self.out / "selected" / "S1.net").exists())
        self.assertTrue((self.out / "selected" / "H1.net").exists())
        self.assertEqual(json.loads((self.out / "progress.json").read_text())["phase"], "done")
        for f in ("candidates.csv", "checks.csv", "measurements.csv", "spec.json", "config.json", "timing.json",
                  "outcome.json"):
            self.assertTrue((self.out / f).exists(), f)

    def test_duplicate_proposal_not_resimulated(self):
        llm = FakeLLM([json.dumps(SSHI_NO_CLAMP), json.dumps(renamed(SSHI_NO_CLAMP, "n1", "mid")),
                       json.dumps(WITNESS)])
        out = run_search(self.cfg(), llm, self.sim, self.rec)
        kinds = [e["kind"] for e in self.events()]
        self.assertIn("duplicate", kinds)
        # reference 6 + sshi 6 + witness 6 + held-out 2 x 4
        self.assertEqual(len(self.backend.calls), 26)
        self.assertIn("duplicate", llm.received[2][1]["content"].lower())
        self.assertEqual(out.stop_reason, "search_spec_met")

    def test_invalid_then_repaired(self):
        bad = {"move": "new_topology", "components": [{"id": "C1", "type": "C", "nodes": ["out", "0"], "value": 9}]}
        llm = FakeLLM([json.dumps(bad), json.dumps(WITNESS)])
        out = run_search(self.cfg(), llm, self.sim, self.rec)
        self.assertEqual(out.selected.origin, "llm")
        self.assertIn("could not be used", llm.received[1][-1]["content"])
        self.assertEqual(out.stop_reason, "search_spec_met")

    def test_invalid_twice_fed_back(self):
        llm = FakeLLM(["no json at all", "still none", json.dumps(WITNESS)])
        run_search(self.cfg(), llm, self.sim, self.rec)
        self.assertIn("rejected", llm.received[2][1]["content"])
        self.assertIn("proposal_invalid", [e["kind"] for e in self.events()])

    def test_search_survives_sim_failure(self):
        llm = FakeLLM([json.dumps(BROKEN), json.dumps(WITNESS)])
        out = run_search(self.cfg(), llm, self.sim, self.rec)
        self.assertIn("simulation failed", llm.received[1][1]["content"])
        self.assertEqual(out.stop_reason, "search_spec_met")

    def test_search_stops_when_model_unavailable(self):
        out = run_search(self.cfg(), FakeLLM([LLMReply(error="HTTP 503")]), self.sim, self.rec)
        self.assertEqual(out.stop_reason, "model_unavailable")
        self.assertEqual(out.selected.origin, "reference")
        self.assertFalse(out.met_all)
        self.assertTrue((self.out / "outcome.json").exists())

    def test_proposal_budget(self):
        out = run_search(self.cfg(max_proposals=2, stagnation=99), FakeLLM([json.dumps(SSHI_NO_CLAMP)]),
                         self.sim, self.rec)
        self.assertEqual(out.stop_reason, "proposal_budget")
        self.assertFalse(out.met_search)
        self.assertIn("sshi", out.selected.name)

    def test_stagnation(self):
        out = run_search(self.cfg(max_proposals=10, stagnation=2), FakeLLM([json.dumps(SSHI_NO_CLAMP)]),
                         self.sim, self.rec)
        self.assertEqual(out.stop_reason, "stagnation")

    def test_model_done(self):
        done = dict(SSHI_NO_CLAMP, done=True)
        out = run_search(self.cfg(min_proposals=1), FakeLLM([json.dumps(done)]), self.sim, self.rec)
        self.assertEqual(out.stop_reason, "model_done")

    def test_heldout_not_in_any_prompt(self):
        llm = FakeLLM([json.dumps(SSHI_NO_CLAMP), json.dumps(WITNESS)])
        run_search(self.cfg(), llm, self.sim, self.rec)
        text = json.dumps(llm.received)
        for h in spec.heldout_conditions():
            self.assertNotIn(f"{h.id}:", text)
            self.assertNotIn(h.label, text)

    def test_refinement_runs_and_is_recorded(self):
        llm = FakeLLM([json.dumps(SSHI_NO_CLAMP)])
        run_search(self.cfg(max_proposals=2, refine_budget=4, refine_min=4, stagnation=99), llm, self.sim, self.rec)
        origins = [l.split(",")[2] for l in (self.out / "candidates.csv").read_text().splitlines()[1:]]
        self.assertIn("refine", origins)

    def test_timing_has_tokens(self):
        run_search(self.cfg(), FakeLLM([json.dumps(WITNESS)]), self.sim, self.rec)
        t = json.loads((self.out / "timing.json").read_text())
        self.assertEqual(t["model_calls"], 1)
        self.assertEqual(t["prompt_tokens"], 100)
        self.assertEqual(t["completion_tokens"], 50)
        for k in ("wall_s", "model_s", "sim_seconds", "sim_wall_s", "n_sims", "cache_hits", "refine_s"):
            self.assertIn(k, t)


if __name__ == "__main__":
    unittest.main()


class SlowLLM:
    def __init__(self):
        self.timeouts = []

    def ask(self, messages, think, max_tokens=None, temperature=None, timeout=None):
        self.timeouts.append(timeout)
        import time as _t
        _t.sleep(5)
        return LLMReply(answer="{}")


class DeadlineTest(unittest.TestCase):
    def test_hung_model_does_not_overrun_wall_clock(self):
        import time as _t
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            llm = SlowLLM()
            t = _t.time()
            res = run_search(SearchConfig(max_proposals=5, wall_clock_s=0.5, model_grace_s=0.3, refine_budget=0,
                                          refine_min=0, heartbeat_s=0.05), llm,
                             Simulator(FakeBackend(physics), out), RunRecorder(out, quiet=True))
            self.assertLess(_t.time() - t, 3.0)
            self.assertEqual(res.stop_reason, "time_budget")
            self.assertIsNotNone(llm.timeouts[0])
            self.assertLessEqual(llm.timeouts[0], 0.5 + 0.3 + 1e-6)
            ev = [json.loads(l) for l in (out / "events.jsonl").read_text().splitlines()]
            self.assertTrue(any(e["kind"] == "model_error" and "budget" in e["error"] for e in ev))
