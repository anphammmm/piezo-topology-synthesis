import csv
import json
import tempfile
import unittest
from pathlib import Path

from piezo_synth import run as run_mod
from piezo_synth.experiments import aggregate, write_paper_tables


class ExperimentsTest(unittest.TestCase):
    def test_aggregate_fake_runs_and_tables(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "exp"
            cfg = Path(d) / "c.json"
            cfg.write_text(json.dumps({"max_rounds": 3, "mc_samples": 2, "size_budget": 4, "size_lambda": 2}))
            for variant, extra in (("full", []), ("random", ["--baseline", "random"])):
                for seed in (1, 2):
                    run_mod.main(["--fake", "--config", str(cfg), "--label", variant, "--seed", str(seed),
                                  "--out", str(root / variant / f"seed{seed}"), *extra])
            runs, summary = aggregate(root)
            self.assertEqual(len(runs), 4)
            self.assertEqual(sorted({r["variant"] for r in runs}), ["full", "random"])
            full = next(s for s in summary if s["variant"] == "full")
            self.assertEqual(full["runs"], 2)
            self.assertEqual(full["success_rate"], 1.0)
            self.assertTrue((root / "experiments.csv").exists())
            with (root / "experiments_summary.csv").open() as f:
                self.assertEqual(len(list(csv.DictReader(f))), 2)
            gen = Path(d) / "gen"
            write_paper_tables(gen, root, smoke=None)
            for name in ("tab_conditions.tex", "tab_criteria.tex", "tab_variants.tex", "tab_screen_audit.tex",
                         "tab_reference.tex", "macros.tex"):
                self.assertTrue((gen / name).exists(), name)
            self.assertIn("full", (gen / "tab_variants.tex").read_text())
            self.assertIn("pending", (gen / "tab_reference.tex").read_text())

    def test_tables_without_runs_say_pending(self):
        with tempfile.TemporaryDirectory() as d:
            gen = Path(d) / "gen"
            write_paper_tables(gen, Path(d) / "none", smoke=None)
            self.assertIn("pending", (gen / "tab_variants.tex").read_text())
            self.assertIn("S1", (gen / "tab_conditions.tex").read_text())


if __name__ == "__main__":
    unittest.main()


class TexEscapeTest(unittest.TestCase):
    def test_generated_tables_are_ascii(self):
        with tempfile.TemporaryDirectory() as d:
            gen = Path(d) / "gen"
            write_paper_tables(gen, Path(d) / "none", smoke=None)
            for f in gen.iterdir():
                text = f.read_text(encoding="utf-8")
                self.assertTrue(text.isascii(), f"{f.name}: {[c for c in text if not c.isascii()]}")


class CampaignTest(unittest.TestCase):
    def test_configs_and_loop(self):
        from piezo_synth.experiments import VARIANTS, campaign_loop, write_campaign_configs
        self.assertIn("full", VARIANTS)
        self.assertIn("random", VARIANTS)
        with tempfile.TemporaryDirectory() as d:
            paths = write_campaign_configs(Path(d) / "exp", base={"max_sims": 3000})
            full = json.loads(paths["full"].read_text())
            self.assertEqual(full["max_sims"], 3000)
            self.assertFalse(json.loads(paths["no_screen"].read_text())["screen"])
        loop = campaign_loop("random", [1, 2], root="runs/exp")
        self.assertNotIn("'", loop)
        for s in ("--label random", "--seed 2", "--baseline random", "runs/exp/random/seed1/outcome.json"):
            self.assertIn(s, loop)
