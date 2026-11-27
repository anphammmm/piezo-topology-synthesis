import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


class NotebookTest(unittest.TestCase):
    def test_notebook_embeds_sources_exactly(self):
        from build_notebook import build
        with tempfile.TemporaryDirectory() as d:
            build(Path(d) / "nb.ipynb")
            nb = json.loads((Path(d) / "nb.ipynb").read_text(encoding="utf-8"))
        self.assertEqual(nb["nbformat"], 4)
        cells = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]
        sources = sorted((ROOT / "piezo_synth").glob("*.py"))
        self.assertGreater(len(sources), 10)
        for f in sources:
            self.assertIn(f"%%writefile piezo_synth/{f.name}\n" + f.read_text(encoding="utf-8"), cells, f.name)
        joined = "\n".join(cells)
        for s in ["--smoke", "progress.json", "run_config.json", "gpus=0", "ltspice-cpu", "read_raw", "report.md", "rm -rf runs/smoke"]:
            self.assertIn(s, joined)
        for c in nb["cells"]:
            if c["cell_type"] == "code":
                self.assertEqual(c["outputs"], [])
                self.assertIsNone(c["execution_count"])

    def test_committed_notebook_is_current(self):
        from build_notebook import build
        with tempfile.TemporaryDirectory() as d:
            build(Path(d) / "nb.ipynb")
            fresh = (Path(d) / "nb.ipynb").read_text(encoding="utf-8")
        self.assertEqual((ROOT / "piezo_synth.ipynb").read_text(encoding="utf-8"), fresh,
                         "run: python tools/build_notebook.py")


if __name__ == "__main__":
    unittest.main()


class SyncNotebookTest(unittest.TestCase):
    def test_sync_notebook_current_and_valid(self):
        from build_sync_notebook import build
        with tempfile.TemporaryDirectory() as d:
            build(Path(d) / "s.ipynb")
            fresh = (Path(d) / "s.ipynb").read_text(encoding="utf-8")
        self.assertEqual((ROOT / "panda_sync.ipynb").read_text(encoding="utf-8"), fresh,
                         "run: python tools/build_sync_notebook.py")
        nb = json.loads(fresh)
        code = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]
        for src in code:
            compile(src, "cell", "exec")
        joined = "\n".join(code)
        for s in ("GIT_ASKPASS", "pull", "--ff-only", "panda_submit", "panda_campaign", "publish_results.py",
                  "runs/paper_generated", 'TASK = "smoke"'):
            self.assertIn(s, joined)
        self.assertNotIn("print(TOKEN", joined)
