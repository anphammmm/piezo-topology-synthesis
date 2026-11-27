import json
import tempfile
import unittest
from pathlib import Path

from piezo_synth import spec


class SpecCheckTest(unittest.TestCase):
    def test_fake_check_writes_summary_per_spec(self):
        from piezo_synth import speccheck
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "sc"
            speccheck.main(["--fake", "--specs", "P1,P2", "--budget", "8", "--out", str(out)])
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual([s["spec"] for s in summary], ["P1", "P2"])
            for s in summary:
                for k in ("reference", "textbook", "witness", "verdict"):
                    self.assertIn(k, s)
                self.assertIn(s["verdict"], ("textbook_solves", "witness_solves", "unproven"))
                self.assertIn("search_pass", s["textbook"])
                self.assertIn("sized_search_pass", s["textbook"])
            self.assertTrue((out / "P2" / "summary.json").exists())
            self.assertIn("| P2 |", (out / "speccheck.md").read_text())
        self.assertEqual(spec.ACTIVE, "P1")

    def test_verdict(self):
        from piezo_synth.speccheck import verdict
        self.assertEqual(verdict(True, True), "textbook_solves")
        self.assertEqual(verdict(False, True), "witness_solves")
        self.assertEqual(verdict(False, False), "unproven")


if __name__ == "__main__":
    unittest.main()
