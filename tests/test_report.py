import json
import shutil
import tempfile
import unittest
from pathlib import Path

from piezo_synth.records import RunRecorder
from piezo_synth.report import build_report
from piezo_synth.search import SearchConfig, run_search
from piezo_synth.sim import Simulator
from tests.fakes import FakeBackend, FakeLLM
from tests.test_search import SSHI_NO_CLAMP, WITNESS, physics


def fake_run(out, replies, **cfg):
    base = dict(max_proposals=4, min_proposals=1, refine_budget=2, refine_min=2, heartbeat_s=0.01)
    base.update(cfg)
    run_search(SearchConfig(**base), FakeLLM(replies), Simulator(FakeBackend(physics), out, workers=2),
               RunRecorder(out, quiet=True))


class ReportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / "run"

    def tearDown(self):
        self.tmp.cleanup()

    def test_report_sections(self):
        fake_run(self.out, [json.dumps(SSHI_NO_CLAMP), json.dumps(WITNESS)])
        text = build_report(self.out)
        heads = ["## Specification", "## Test conditions", "## Reference results", "## Proposals tried",
                 "## Selected design", "## Held-out check", "## Unmet requirements", "## Stop reason",
                 "## Time and tokens", "## Files"]
        pos = [text.index(h) for h in heads]
        self.assertEqual(pos, sorted(pos))
        self.assertIn("search_spec_met", text)
        self.assertIn("sshi + clamp", text)
        self.assertIn("H3", text)
        self.assertTrue((self.out / "report.md").exists())
        s = json.loads((self.out / "summary.json").read_text())
        self.assertEqual(s["stop_reason"], "search_spec_met")
        self.assertTrue(s["met_all"])
        self.assertEqual(s["failed_checks"], [])
        self.assertIn("model_calls", s["timing"])

    def test_unmet_requirements_listed(self):
        fake_run(self.out, [json.dumps(SSHI_NO_CLAMP)], max_proposals=2, stagnation=99)
        text = build_report(self.out)
        unmet = text[text.index("## Unmet requirements"):text.index("## Stop reason")]
        self.assertIn("vout_max", unmet)
        s = json.loads((self.out / "summary.json").read_text())
        self.assertFalse(s["met_search"])
        self.assertTrue(any(f["criterion"] == "vout_max" for f in s["failed_checks"]))

    def test_report_from_partial_run(self):
        fake_run(self.out, [json.dumps(SSHI_NO_CLAMP), json.dumps(WITNESS)])
        part = Path(self.tmp.name) / "partial"
        shutil.copytree(self.out, part)
        for f in ("progress.json", "outcome.json", "timing.json", "report.md", "summary.json"):
            (part / f).unlink(missing_ok=True)
        ev = (part / "events.jsonl").read_text().splitlines()
        (part / "events.jsonl").write_text("\n".join(ev[: len(ev) // 2]) + "\n")
        build_report(part)
        s = json.loads((part / "summary.json").read_text())
        self.assertEqual(s["stop_reason"], "incomplete")
        self.assertIsNotNone(s["selected_id"])

    def test_report_survives_half_written_rows(self):
        fake_run(self.out, [json.dumps(SSHI_NO_CLAMP), json.dumps(WITNESS)])
        (self.out / "outcome.json").unlink()
        with (self.out / "candidates.csv").open("a") as f:
            f.write("c0099,7,llm,,new_topology,cut,abc,def,5,search,")
        with (self.out / "checks.csv").open("a") as f:
            f.write("c0099,search,S1,vout_min,1.2,>=,")
        build_report(self.out)
        s = json.loads((self.out / "summary.json").read_text())
        self.assertEqual(s["stop_reason"], "incomplete")
        self.assertNotEqual(s["selected_id"], "c0099")


if __name__ == "__main__":
    unittest.main()
