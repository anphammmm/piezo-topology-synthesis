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


class ScreenValidationTableTest(unittest.TestCase):
    def test_table_from_smoke_and_pending_without(self):
        with tempfile.TemporaryDirectory() as d:
            run_mod.main(["--fake", "--smoke", "--out", str(Path(d) / "smoke")])
            gen = Path(d) / "gen"
            write_paper_tables(gen, Path(d) / "none", smoke=Path(d) / "smoke")
            t = (gen / "tab_screen_validation.tex").read_text()
            for s in ("S2", "S4", "S6", "FBR", "Witness"):
                self.assertIn(s, t)
            self.assertNotIn("pending", t)
            self.assertIn(chr(92) + "bar V", t)
            self.assertFalse([c for c in t if ord(c) < 32 and c not in chr(10) + chr(9)])
            write_paper_tables(gen, Path(d) / "none", smoke=None)
            self.assertIn("pending", (gen / "tab_screen_validation.tex").read_text())


class RandomBaselineBudgetTest(unittest.TestCase):
    """The random baseline must spend the same simulation budget as the model variants: in the first
    campaign it stopped on stagnation after 5 rounds (353 of 3000 simulations)."""

    def test_random_variant_is_stopped_only_by_budget(self):
        from piezo_synth.experiments import VARIANTS
        over = VARIANTS["random"][0]
        self.assertGreaterEqual(over.get("stagnation", 0), 10 ** 6)
        self.assertGreaterEqual(over.get("max_rounds", 0), 10 ** 4)


class SpreadAndSignificanceTest(unittest.TestCase):
    def test_fisher_exact_two_sided(self):
        from piezo_synth.experiments import fisher_two_sided
        self.assertAlmostEqual(fisher_two_sided(5, 5, 0, 5), 2 / 252, places=6)
        self.assertAlmostEqual(fisher_two_sided(1, 5, 2, 5), 1.0, places=6)

    def test_variants_table_shows_range(self):
        from piezo_synth.experiments import _variants_table
        s = {"variant": "full", "runs": 5, "success_rate": 1.0, "met_all_rate": 0.2,
             "median_sims_to_success": 147, "min_sims_to_success": 27, "max_sims_to_success": 291,
             "median_time_to_success_s": 425, "median_sims": 315, "invalid_rate": 0.0, "median_mc_pass": 0.5}
        self.assertIn("147 [27--291]", _variants_table([s]))


class CostTableAndMacrosTest(unittest.TestCase):
    def test_cost_table_and_significance_macros(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "exp"
            cfg = Path(d) / "c.json"
            cfg.write_text(json.dumps({"max_rounds": 3, "mc_samples": 2, "size_budget": 4, "size_lambda": 2}))
            for variant, extra in (("full", []), ("random", ["--baseline", "random"])):
                run_mod.main(["--fake", "--config", str(cfg), "--label", variant, "--seed", "1",
                              "--out", str(root / variant / "seed1"), *extra])
            gen = Path(d) / "gen"
            write_paper_tables(gen, root, smoke=None)
            cost = (gen / "tab_cost.tex").read_text()
            self.assertIn("full", cost)
            self.assertIn("tokens", cost)
            macros = (gen / "macros.tex").read_text()
            for name in ("RandomVsFullP", "MinPairP", "RandomMedianSims"):
                self.assertIn("\\" + name + "}", macros)
