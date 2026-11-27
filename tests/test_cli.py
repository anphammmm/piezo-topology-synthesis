import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def run(*args):
    return subprocess.run([sys.executable, "-m", *args], capture_output=True, text=True, timeout=120)


class CLITest(unittest.TestCase):
    def test_cli_fake_run(self):
        with tempfile.TemporaryDirectory() as d:
            p = run("piezo_synth.run", "--fake", "--out", str(Path(d) / "r"))
            self.assertEqual(p.returncode, 0, p.stderr[-2000:])
            self.assertTrue((Path(d) / "r" / "report.md").exists())
            self.assertIn("[model", p.stdout)
            self.assertIn("[sim", p.stdout)

    def test_cli_fake_smoke_and_reproduce(self):
        with tempfile.TemporaryDirectory() as d:
            p = run("piezo_synth.run", "--fake", "--smoke", "--out", str(Path(d) / "s"))
            self.assertEqual(p.returncode, 0, p.stderr[-2000:])
            s = json.loads((Path(d) / "s" / "summary.json").read_text())
            self.assertEqual(s["stop_reason"], "smoke")
            self.assertIn("[screen", p.stdout)
            scr = json.loads((Path(d) / "s" / "smoke_screen.json").read_text())
            self.assertEqual(sorted(scr), ["reference", "witness"])
            circ = Path(d) / "s" / "candidates" / "c0001" / "circuit.json"
            p = run("piezo_synth.reproduce", str(circ), "--out", str(Path(d) / "rep"), "--conditions", "S1,H2",
                    "--fake", "--waveforms")
            self.assertEqual(p.returncode, 0, p.stderr[-2000:])
            self.assertIn("H2", p.stdout)
            rep = json.loads((Path(d) / "rep" / "reproduce.json").read_text())
            self.assertEqual(sorted(rep["conditions"]), ["H2", "S1"])


if __name__ == "__main__":
    unittest.main()


class FindRawTest(unittest.TestCase):
    def test_finds_raw_in_subfolder_and_skips_op_raw(self):
        from piezo_synth.reproduce import find_raw
        with tempfile.TemporaryDirectory() as d:
            sub = Path(d) / "work" / "deep"
            sub.mkdir(parents=True)
            (Path(d) / "circuit.op.raw").write_bytes(b"x")
            (sub / "circuit.raw").write_bytes(b"x")
            self.assertEqual(Path(find_raw(d)).name, "circuit.raw")

    def test_none_when_missing(self):
        from piezo_synth.reproduce import find_raw
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(find_raw(d))
            self.assertIsNone(find_raw(Path(d) / "absent"))
