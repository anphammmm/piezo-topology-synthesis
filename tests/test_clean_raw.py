import tempfile
import unittest
from pathlib import Path

from tools import clean_raw


class CleanRawTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runs = Path(self.tmp.name) / "runs"
        for rel in ("exp/full/seed1/sims/a/c.raw", "exp/full/seed1/sims/a/c.op.raw", "smoke/sims/b/c.raw",
                    "single-1/waves-selected/sims/c/c.raw"):
            p = self.runs / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"\0" * 1000)
        (self.runs / "smoke" / "sims" / "b" / "c.log").write_text("log")

    def tearDown(self):
        self.tmp.cleanup()

    def remaining(self):
        return sorted(p.relative_to(self.runs).as_posix() for p in self.runs.rglob("*.raw"))

    def test_dry_run_deletes_nothing(self):
        n, size = clean_raw.clean(self.runs, delete=False)
        self.assertEqual((n, size), (3, 3000))
        self.assertEqual(len(self.remaining()), 4)

    def test_delete_keeps_waveform_runs_and_logs(self):
        clean_raw.clean(self.runs, delete=True)
        self.assertEqual(self.remaining(), ["single-1/waves-selected/sims/c/c.raw"])
        self.assertTrue((self.runs / "smoke" / "sims" / "b" / "c.log").exists())


if __name__ == "__main__":
    unittest.main()
