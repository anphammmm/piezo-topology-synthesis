import copy
import csv
import json
import re
import tempfile
import unittest
from pathlib import Path

from piezo_synth import spec
from piezo_synth.baselines import RandomProposer
from piezo_synth.circuit import to_dict
from piezo_synth.llm import LLMReply
from piezo_synth.netlist import reference_circuit, witness_circuit
from piezo_synth.records import RunRecorder
from piezo_synth.search import SearchConfig, run_search
from piezo_synth.sim import Simulator
from tests.fakes import FakeBackend, FakeLLM

GOOD = dict(vavg=2.5, vavg_prev=2.49, vpp=0.02, vmax=2.6, tup=0.2, pload=1e-5, pext=2e-5)
POOR = dict(vavg=1.2, vavg_prev=1.19, vpp=0.03, vmax=1.3, pload=1e-6, pext=2e-6)   # no tup
PINNED = dict(vavg=0.6, vavg_prev=0.6, vpp=0.01, vmax=0.65, pload=1e-9, pext=1e-6)


def uses(text, model):
    return re.search(rf"^[DS]\w* .* {model}$", text, re.M) is not None


def screen_meas(text, ratio):
    cid = re.search(r"condition (S\d)", text).group(1)
    need = spec.SCREEN["vstore"] ** 2 / spec.condition(cid).rl
    return {"isn": need * ratio * spec.SCREEN["rsense"] / spec.SCREEN["vstore"], "vout": 1.8}


def physics(text):
    if uses(text, "DSI"):
        return None                         # this design does not simulate
    if "Vst vsn" in text:                   # screening bench
        return screen_meas(text, 2.0 if uses(text, "SWI") else 0.3)
    if uses(text, "DZ33") and uses(text, "SWI"):
        return GOOD
    if uses(text, "SWI"):
        return dict(GOOD, vmax=4.0)         # better: only overvoltage fails
    return POOR


def pinned(text):
    return screen_meas(text, 0.0) if "Vst vsn" in text else PINNED


WITNESS = dict(to_dict(witness_circuit()), move="new_topology", name="sshi + clamp")
SSHI_NO_CLAMP = copy.deepcopy(WITNESS)
SSHI_NO_CLAMP["components"] = [c for c in SSHI_NO_CLAMP["components"] if c.get("model") != "DZ33"]
SSHI_NO_CLAMP["name"] = "sshi"
SSHI_OTHER_VALUES = copy.deepcopy(SSHI_NO_CLAMP)
for _c in SSHI_OTHER_VALUES["components"]:
    if _c["id"] == "L1":
        _c["value"] = 1e-3
BROKEN = copy.deepcopy(SSHI_NO_CLAMP)
for comp in BROKEN["components"]:
    if comp.get("model") == "DSCH":
        comp["model"] = "DSI"
BRIDGE_CLAMP = dict(to_dict(reference_circuit()), move="new_topology", name="bridge + clamp")
BRIDGE_CLAMP["components"] = BRIDGE_CLAMP["components"] + [
    {"id": "D5", "type": "D", "nodes": ["0", "out"], "model": "DZ33"}]


def multi(*designs):
    return json.dumps({"proposals": list(designs)})


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
        base = dict(max_rounds=6, min_rounds=1, proposals_per_round=3, size_budget=8, size_lambda=4,
                    size_min_gens=1, mc_samples=0, heartbeat_s=0.01, drain_top=1)
        base.update(kw)
        return SearchConfig(**base)

    def events(self):
        return [json.loads(l) for l in (self.out / "events.jsonl").read_text().splitlines()]

    def proposals(self):
        with (self.out / "proposals.csv").open() as f:
            return list(csv.DictReader(f))

    def origins(self):
        with (self.out / "candidates.csv").open() as f:
            return [r["origin"] for r in csv.DictReader(f)]

    def test_search_meets_spec_and_runs_heldout(self):
        out = run_search(self.cfg(mc_samples=3), FakeLLM([multi(WITNESS)]), self.sim, self.rec)
        self.assertEqual(out.stop_reason, "search_spec_met")
        self.assertTrue(out.met_search)
        self.assertTrue(out.met_all)
        self.assertEqual({c.condition for c in out.heldout_selected.checks}, {"H1", "H2", "H3", "H4"})
        self.assertEqual({c.condition for c in out.heldout_reference.checks}, {"H1", "H2", "H3", "H4"})
        for f in ("candidates.csv", "checks.csv", "measurements.csv", "spec.json", "config.json", "timing.json",
                  "outcome.json", "proposals.csv", "robust.json", "reference_screen.json",
                  "selected/circuit.json", "selected/S1.net", "selected/H1.net"):
            self.assertTrue((self.out / f).exists(), f)
        self.assertEqual(json.loads((self.out / "progress.json").read_text())["phase"], "done")
        self.assertEqual(json.loads((self.out / "robust.json").read_text())["n"], 3)

    def test_several_designs_per_round_each_screened(self):
        llm = FakeLLM([multi(BRIDGE_CLAMP, WITNESS)])
        out = run_search(self.cfg(), llm, self.sim, self.rec)
        self.assertEqual(out.stop_reason, "search_spec_met")
        self.assertEqual([p["status"] for p in self.proposals()], ["screen_failed", "evaluated"])
        self.assertAlmostEqual(float(self.proposals()[0]["worst_ratio"]), 0.3, places=6)

    def test_screen_failed_design_reported_and_not_sized(self):
        llm = FakeLLM([multi(BRIDGE_CLAMP), multi(WITNESS)])
        run_search(self.cfg(), llm, self.sim, self.rec)
        p2 = llm.received[1][1]["content"]
        self.assertIn("failed the screen", p2)
        self.assertIn("30 % of the load's need", p2)
        self.assertNotIn("size", self.origins())

    def test_same_topology_is_duplicate_even_with_new_values(self):
        llm = FakeLLM([multi(SSHI_NO_CLAMP), multi(SSHI_OTHER_VALUES), multi(WITNESS)])
        out = run_search(self.cfg(), llm, self.sim, self.rec)
        self.assertIn("duplicate", [p["status"] for p in self.proposals()])
        self.assertIn("duplicate", llm.received[2][1]["content"].lower())
        self.assertEqual(out.stop_reason, "search_spec_met")

    def test_sizing_runs_while_model_thinks(self):
        llm = FakeLLM([multi(SSHI_NO_CLAMP), multi(SSHI_NO_CLAMP)])
        run_search(self.cfg(max_rounds=2, stagnation=99), llm, self.sim, self.rec)
        self.assertIn("size", self.origins())
        self.assertIn("value sizing", llm.received[1][1]["content"])

    def test_invalid_then_repaired(self):
        bad = {"move": "new_topology", "components": [{"id": "C1", "type": "C", "nodes": ["out", "0"], "value": 9}]}
        llm = FakeLLM([multi(bad), multi(WITNESS)])
        out = run_search(self.cfg(), llm, self.sim, self.rec)
        self.assertEqual(out.selected.origin, "llm")
        self.assertIn("could not be used", llm.received[1][-1]["content"])
        self.assertEqual(out.stop_reason, "search_spec_met")

    def test_invalid_twice_fed_back(self):
        llm = FakeLLM(["no json at all", "still none", multi(WITNESS)])
        run_search(self.cfg(), llm, self.sim, self.rec)
        self.assertIn("rejected", llm.received[2][1]["content"])
        self.assertIn("proposal_invalid", [e["kind"] for e in self.events()])

    def test_search_survives_sim_failure(self):
        llm = FakeLLM([multi(BROKEN), multi(WITNESS)])
        out = run_search(self.cfg(), llm, self.sim, self.rec)
        self.assertIn("simulation failed", llm.received[1][1]["content"])
        self.assertEqual(out.stop_reason, "search_spec_met")

    def test_search_stops_when_model_unavailable(self):
        out = run_search(self.cfg(), FakeLLM([LLMReply(error="HTTP 503")]), self.sim, self.rec)
        self.assertEqual(out.stop_reason, "model_unavailable")
        self.assertEqual(out.selected.origin, "reference")
        self.assertFalse(out.met_all)

    def test_round_budget(self):
        out = run_search(self.cfg(max_rounds=2, stagnation=99), FakeLLM([multi(SSHI_NO_CLAMP)]), self.sim, self.rec)
        self.assertEqual(out.stop_reason, "round_budget")
        self.assertFalse(out.met_search)
        self.assertIn("sshi", out.selected.name)

    def test_stagnation(self):
        out = run_search(self.cfg(max_rounds=10, stagnation=2, size_budget=0), FakeLLM([multi(SSHI_NO_CLAMP)]),
                         self.sim, self.rec)
        self.assertEqual(out.stop_reason, "stagnation")

    def test_model_done(self):
        done = dict(SSHI_NO_CLAMP, done=True)
        out = run_search(self.cfg(), FakeLLM([multi(done)]), self.sim, self.rec)
        self.assertEqual(out.stop_reason, "model_done")

    def test_sim_budget(self):
        out = run_search(self.cfg(max_rounds=50, stagnation=99, max_sims=60), FakeLLM([multi(SSHI_NO_CLAMP),
                         multi(BRIDGE_CLAMP)]), self.sim, self.rec)
        self.assertEqual(out.stop_reason, "sim_budget")

    def test_heldout_not_in_any_prompt(self):
        llm = FakeLLM([multi(SSHI_NO_CLAMP), multi(WITNESS)])
        run_search(self.cfg(), llm, self.sim, self.rec)
        text = json.dumps(llm.received)
        for h in spec.heldout_conditions():
            self.assertNotIn(f"{h.id}:", text)
            self.assertNotIn(h.label, text)

    def test_no_screen_ablation_simulates_no_screen_bench(self):
        run_search(self.cfg(screen=False), FakeLLM([multi(WITNESS)]), self.sim, self.rec)
        self.assertFalse(any("Vst vsn" in t for t in self.backend.calls))

    def test_repeated_problem_flagged_and_dead_not_sized(self):
        sim = Simulator(FakeBackend(pinned), self.out / "p", workers=4)
        llm = FakeLLM([multi(WITNESS), multi(SSHI_NO_CLAMP), multi(BRIDGE_CLAMP), multi(BRIDGE_CLAMP)])
        run_search(self.cfg(screen=False, max_rounds=4, stagnation=99, proposals_per_round=1), llm, sim, self.rec)
        self.assertIn("REPEATED", llm.received[3][1]["content"])
        self.assertNotIn("size", self.origins())

    def test_no_diagnostics_ablation(self):
        sim = Simulator(FakeBackend(pinned), self.out / "p", workers=4)
        llm = FakeLLM([multi(WITNESS), multi(SSHI_NO_CLAMP), multi(BRIDGE_CLAMP), multi(BRIDGE_CLAMP)])
        run_search(self.cfg(screen=False, diagnostics=False, max_rounds=4, stagnation=99), llm, sim, self.rec)
        text = json.dumps(llm.received)
        self.assertNotIn("REPEATED", text)
        self.assertNotIn("what this means", text)

    def test_screen_audit_sizes_rejected_but_never_selects_them(self):
        out = run_search(self.cfg(screen_audit=True, max_rounds=1), FakeLLM([multi(BRIDGE_CLAMP)]), self.sim, self.rec)
        self.assertIn("audit", self.origins())
        self.assertNotEqual(out.selected.origin, "audit")
        self.assertIn("audit", [e["kind"] for e in self.events()])

    def test_random_baseline_runs(self):
        never = FakeBackend(lambda t: None if uses(t, "DSI") else
                            screen_meas(t, 2.0) if "Vst vsn" in t else dict(GOOD, vmax=4.0))
        sim = Simulator(never, self.out / "r", workers=4)
        out = run_search(self.cfg(max_rounds=3, stagnation=99), RandomProposer(seed=3), sim, self.rec)
        self.assertEqual(out.stop_reason, "round_budget")
        self.assertEqual(len(self.proposals()), 9)

    def test_timing_has_tokens(self):
        run_search(self.cfg(), FakeLLM([multi(WITNESS)]), self.sim, self.rec)
        t = json.loads((self.out / "timing.json").read_text())
        self.assertEqual(t["model_calls"], 1)
        self.assertEqual(t["prompt_tokens"], 100)
        self.assertEqual(t["completion_tokens"], 50)
        for k in ("wall_s", "model_s", "sim_seconds", "sim_wall_s", "n_sims", "cache_hits", "size_s", "screen_s",
                  "n_screen_sims"):
            self.assertIn(k, t)


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
            res = run_search(SearchConfig(max_rounds=5, wall_clock_s=0.5, model_grace_s=0.3, size_budget=0,
                                          mc_samples=0, heartbeat_s=0.05), llm,
                             Simulator(FakeBackend(physics), out), RunRecorder(out, quiet=True))
            self.assertLess(_t.time() - t, 3.0)
            self.assertEqual(res.stop_reason, "time_budget")
            self.assertIsNotNone(llm.timeouts[0])
            self.assertLessEqual(llm.timeouts[0], 0.5 + 0.3 + 1e-6)
            ev = [json.loads(l) for l in (out / "events.jsonl").read_text().splitlines()]
            self.assertTrue(any(e["kind"] == "model_error" and "budget" in e["error"] for e in ev))


if __name__ == "__main__":
    unittest.main()


class FirstFastThenSlowLLM:
    """Round 1 answers at once; round 2 takes a long time (the model is still thinking)."""

    def __init__(self, first):
        self.first, self.calls = first, 0

    def ask(self, messages, think, max_tokens=None, temperature=None, timeout=None):
        import time as _t
        self.calls += 1
        if self.calls == 1:
            return LLMReply(answer=self.first, seconds=0.0, prompt_tokens=10, completion_tokens=5)
        _t.sleep(5)
        return LLMReply(answer=multi(BRIDGE_CLAMP), seconds=5.0, prompt_tokens=10, completion_tokens=5)


class StopWhenMetDuringWaitTest(unittest.TestCase):
    def test_spec_met_by_sizing_stops_without_waiting_for_the_model(self):
        import time as _t

        def proposed_values_fail(text):          # any sized variant passes; the proposed values do not
            if not uses(text, "SWI"):
                return POOR                       # the reference bridge fails
            if "100n 100n 3.4e-05 " in text:
                return dict(GOOD, vmax=4.0)
            return GOOD
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            t = _t.time()
            res = run_search(SearchConfig(max_rounds=4, min_rounds=1, screen=False, size_budget=8, size_lambda=4,
                                          mc_samples=0, heartbeat_s=0.05, stagnation=99),
                             FirstFastThenSlowLLM(multi(WITNESS)), Simulator(FakeBackend(proposed_values_fail), out),
                             RunRecorder(out, quiet=True))
            self.assertLess(_t.time() - t, 4.0)
            self.assertEqual(res.stop_reason, "search_spec_met")
            self.assertEqual(res.selected.origin, "size")
            rows = (out / "proposals.csv").read_text().splitlines()
            self.assertEqual(len(rows), 2)          # header + round 1 only: round 2 never processed
