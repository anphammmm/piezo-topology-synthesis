import json
import sys
import tempfile
import unittest
from pathlib import Path

from piezo_synth import run as run_mod
from piezo_synth.experiments import aggregate

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))


def fake_run(root: Path, spec: str, variant: str, seed: int, neutral: bool = False) -> Path:
    """A finished run. neutral=False imitates the first benchmark's code, whose config.json had no
    hinted_prompt key (it always used the original prompt)."""
    cfg = root / "c.json"
    cfg.write_text(json.dumps({"max_rounds": 2, "mc_samples": 0, "size_budget": 4, "size_lambda": 2}))
    out = root / "bench" / spec / variant / f"seed{seed}"
    run_mod.main(["--fake", "--spec", spec, "--config", str(cfg), "--label", variant, "--seed", str(seed),
                  "--out", str(out)])
    (root / "bench" / f"{spec}-{variant}-seed{seed}.log").write_text("log\n")
    if not neutral:
        c = json.loads((out / "config.json").read_text())
        c.pop("hinted_prompt", None)
        (out / "config.json").write_text(json.dumps(c))
    return out


class MigrateHintedTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.old, self.new = self.root / "bench", self.root / "bench2"
        self.src = fake_run(self.root, "P1", "full", 1)

    def tearDown(self):
        self.tmp.cleanup()

    def test_dry_run_touches_nothing(self):
        from migrate_hinted import migrate
        moves = migrate(self.old, self.new, apply=False)
        self.assertEqual(len(moves), 1)
        self.assertTrue(self.src.exists())
        self.assertFalse(self.new.exists())

    def test_apply_moves_finished_runs_and_relabels(self):
        from migrate_hinted import migrate
        migrate(self.old, self.new, apply=True)
        runs, _ = aggregate(self.new)
        self.assertEqual([(r["spec"], r["variant"]) for r in runs], [("P1", "hinted")])
        self.assertFalse(self.src.exists())
        dest = self.new / "P1" / "hinted" / "seed1"
        meta = json.loads((dest / "run_meta.json").read_text())
        self.assertEqual(meta["label"], "hinted")
        self.assertIn("P1/full/seed1", meta["migrated_from"])
        self.assertTrue((self.new / "P1-hinted-seed1.log").exists())
        self.assertFalse((self.old / "P1-full-seed1.log").exists())

    def test_unfinished_run_stays(self):
        from migrate_hinted import migrate
        half = self.old / "P2" / "full" / "seed1"
        half.mkdir(parents=True)
        (half / "progress.json").write_text("{}")
        migrate(self.old, self.new, apply=True)
        self.assertTrue(half.exists())
        self.assertFalse((self.new / "P2").exists())

    def test_second_run_moves_nothing(self):
        from migrate_hinted import migrate
        migrate(self.old, self.new, apply=True)
        self.assertEqual(migrate(self.old, self.new, apply=True), [])

    def test_existing_destination_is_not_overwritten(self):
        from migrate_hinted import migrate
        dest = self.new / "P1" / "hinted" / "seed1"
        dest.mkdir(parents=True)
        (dest / "outcome.json").write_text('{"keep": true}')
        self.assertEqual(migrate(self.old, self.new, apply=True), [])
        self.assertTrue(self.src.exists())
        self.assertEqual(json.loads((dest / "outcome.json").read_text()), {"keep": True})

    def test_neutral_prompt_run_is_not_migrated(self):
        """An old-bench seed that started after the new code was pulled used the neutral prompt."""
        from migrate_hinted import migrate
        late = fake_run(self.root, "P5", "full", 3, neutral=True)
        moves = migrate(self.old, self.new, apply=True)
        self.assertEqual([m[1].split("/")[-3] for m in moves], ["P1"])
        self.assertTrue(late.exists())
        self.assertFalse((self.new / "P5").exists())

    def test_other_variants_untouched(self):
        from migrate_hinted import migrate
        other = fake_run(self.root, "P1", "no_screen", 1)
        migrate(self.old, self.new, apply=True)
        self.assertTrue(other.exists())


if __name__ == "__main__":
    unittest.main()
