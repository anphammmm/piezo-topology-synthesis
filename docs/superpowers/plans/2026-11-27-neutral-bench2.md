# Neutral prompt by default, benchmark v2 (bench2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the hint-free system prompt the default, re-run the benchmark as `runs/bench2` with fewer runs, and keep the finished hinted-prompt runs as the `hinted` variant instead of re-running them.

**Architecture:** `SearchConfig.neutral_prompt` (local commit f5b6728, not pushed) becomes `hinted_prompt: bool = False`, so the default prompt is neutral and the old prompt is the `hinted` variant. The benchmark moves to `runs/bench2` with variants full, no_screen, no_diag, hinted (5 seeds) and random (3 seeds). Finished `runs/bench/<spec>/full/seed<n>` runs used the old prompt, so a migration tool moves them to `runs/bench2/<spec>/hinted/seed<n>`, and the loop skips them. A notebook task `"bench2"` stops the old bench jobs, migrates, and submits.

**Tech Stack:** Python 3 stdlib, unittest (`python3 -m unittest discover -s tests -t .`), Jupyter notebook generators in `tools/`.

**Spec:** decisions taken in the conversation of 2026-11-27 (no separate spec file):
- the neutral prompt is the default for every variant;
- the old bench results are kept as the `hinted` variant;
- coord is dropped from the benchmark, and random runs 3 seeds per spec.

## Global Constraints

- The neutral prompt keeps the spec, the component vocabulary (L, S, SYNC still described) and the FBR reference. It drops three things:
  - the SSHI JSON example (L 4.7 mH, S, SYNC ton 3.4e-05);
  - `ton is about pi*sqrt(L*Cp)`;
  - the full-bridge and zener-clamp wiring examples (`["0", "out"]`, `["0", "pzp"]`).
- `hinted_prompt=True` reproduces the old prompt exactly, character for character.
- Benchmark root is `runs/bench2`. Variants and seeds:
  - `["full", "no_screen", "no_diag", "hinted", "random"]`, seeds 1-5;
  - random: seeds 1-3 only.
- Bench2 job names are `piezo-bench2-<spec lower>`, so they do not collide with the logs of the old `piezo-bench-p*` jobs.
- Never delete anything under `runs/`. The migration moves only finished runs (folder with `outcome.json`), never overwrites a destination, and records where each run came from.
- The notebook may cancel only jobs listed in `runs/jobs.jsonl` whose name matches `piezo-bench-p[1-5]` exactly (CLAUDE.md rule 2).
- After any change in `piezo_synth/`, run `python3 tools/build_notebook.py`. After changing `tools/build_sync_notebook.py`, run `python3 tools/build_sync_notebook.py`.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. No push without asking.

## Review Focus

1. **Old bench jobs still running while the new code is pulled.** Their configs `runs/bench/*.json` have no `hinted_prompt` key, so they would silently switch to the neutral prompt. The `"bench2"` task cancels them first. The task text and README must say to run `"bench2"` right after pulling.
2. **Migrating while a cancelled pod still writes.** Only folders with `outcome.json` move, so a half-written run stays behind. Test: a seed folder without `outcome.json` is not moved.
3. **Running the migration twice.** The destination already exists, so it is skipped, and the second run moves nothing. Test in Task 3.
4. **Migrated runs counted as `full`.** `run_meta.json` label `full` must become `hinted`, otherwise `aggregate` groups them as `full`. Test in Task 3 through `aggregate`.
5. **Config files written by older code** containing `"neutral_prompt"`. `run.py` drops unknown keys (`load_config` filters by dataclass fields), so the run uses the default neutral prompt. Test in Task 1.

---

### Task 1: Neutral prompt is the default; `hinted` variant

**Files:**
- Modify: `piezo_synth/prompts.py`: rename the parameter `neutral` to `hinted: bool = False` and invert the three conditionals.
- Modify: `piezo_synth/search.py`: rename `SearchConfig.neutral_prompt` to `hinted_prompt: bool = False`, and pass `hinted=cfg.hinted_prompt`.
- Modify: `piezo_synth/experiments.py`:
  - in `VARIANTS`, replace `"neutral_prompt"` with `"hinted": ({"hinted_prompt": True}, "")`;
  - in `VARIANT_ORDER`, replace `"neutral_prompt"` with `"hinted"`.
- Test: `tests/test_prompts.py`, `tests/test_search.py`, `tests/test_experiments.py`, `tests/test_cli.py` (or wherever `load_config` is tested).

**Interfaces:**
- Produces:
  - `system_prompt(reference_eval, per_round=3, screen=True, size_budget=48, hinted=False) -> str`;
  - `SearchConfig.hinted_prompt: bool`;
  - `VARIANTS["hinted"]`.

- [ ] **Step 1: Update the tests first**
  - `test_prompts.py`:
    - rename `test_neutral_prompt_hides_textbook_fragments` to `test_default_prompt_hides_textbook_fragments`. It calls `system_prompt(REF_EV)` with the same `assertNotIn` and `assertIn` lists, and its last block checks that `system_prompt(REF_EV, hinted=True)` contains `"pi*sqrt"` and `'"type": "SYNC"'`;
    - `test_system_prompt_explains_diode_orientation` calls `system_prompt(REF_EV, hinted=True)`.
  - `test_search.py`: `test_hinted_prompt_config_reaches_the_model`. `self.cfg(hinted_prompt=True)` gives a system message with `"pi*sqrt"`; `self.cfg()` gives one without it.
  - `test_experiments.py`:
    - `VARIANTS["hinted"] == ({"hinted_prompt": True}, "")`;
    - `"neutral_prompt" not in VARIANTS`;
    - the bench table test uses variant `"hinted"` and asserts `"hinted"` appears in the table.
  - New test `test_config_ignores_unknown_neutral_prompt_key`: `run.load_config` (the function at `piezo_synth/run.py:~149`) is given a JSON file `{"neutral_prompt": true}` and returns `hinted_prompt is False`.
- [ ] **Step 2: Run them and confirm they fail**
  - Run: `python3 -m unittest tests.test_prompts tests.test_search tests.test_experiments`
  - Expected: failures that name `hinted`.
- [ ] **Step 3: Implement the rename and inversion** in the three modules above.
- [ ] **Step 4: Run the tests**
  - Run: `python3 tools/build_notebook.py && python3 -m unittest discover -s tests -t .`
  - Expected: `OK`. Some tests still use `neutral_prompt`: notebook task `"neutral"` and the panda_submit extra-variant test. Change them to use `hinted`; Task 4 removes the `"neutral"` task.
- [ ] **Step 5: Commit**: `feat: neutral system prompt by default; the old prompt is the hinted variant`.

### Task 2: Benchmark v2 layout (root, variants, random seeds, job names)

**Files:**
- Modify: `piezo_synth/experiments.py`:
  - set `BENCH_VARIANTS`, add `BENCH_ROOT = "runs/bench2"` and `BENCH_RANDOM_SEEDS = 3`;
  - `bench_loop` gets a default root of `BENCH_ROOT` and caps random seeds;
  - remove `BENCH_EXTRA`; `_bench_table` columns come from `BENCH_VARIANTS`.
- Modify: `tools/panda_campaign.py`: `--bench` writes configs to `runs/bench2`, and job names become `piezo-bench2-<spec>`, plus the existing variant suffix for custom `--variants`.
- Test: `tests/test_experiments.py` (`BenchmarkTest`), `tests/test_panda_submit.py`.

**Interfaces:**
- Produces:
  - `BENCH_VARIANTS = ["full", "no_screen", "no_diag", "hinted", "random"]`;
  - `BENCH_ROOT = "runs/bench2"`;
  - `BENCH_RANDOM_SEEDS = 3`;
  - `bench_loop(spec_name, variants, seeds, root=BENCH_ROOT) -> str`, where random runs use `seeds[:BENCH_RANDOM_SEEDS]`.

- [ ] **Step 1: Write the failing tests**
  - `test_bench_loop_command`:
    - `BENCH_VARIANTS` equals the list above;
    - `cmd = bench_loop("P2", BENCH_VARIANTS, [1, 2, 3, 4, 5])`. In `cmd`:
      - `"runs/bench2/P2/random/seed3/outcome.json"` is in `cmd`;
      - `"runs/bench2/P2/random/seed4"` is not in `cmd`;
      - `"runs/bench2/P2/hinted/seed5"` is in `cmd`;
      - `"coord"` is not in `cmd`;
      - `"'"` is not in `cmd`.
  - `test_bench_submits_one_job_per_spec`:
    - names are `["piezo-bench2-p2", "piezo-bench2-p3"]`;
    - the command contains `runs/bench2/P2/hinted/seed1`;
    - `runs/bench2/hinted.json` exists and contains `"hinted_prompt": true`.
  - `test_bench_extra_variant_gets_its_own_job_names`: `--variants hinted` gives `piezo-bench2-p1-hinted`.
- [ ] **Step 2: Run and confirm they fail**
  - Run: `python3 -m unittest tests.test_experiments tests.test_panda_submit`
  - Expected: FAIL on `bench2` and `hinted`.
- [ ] **Step 3: Implement** the constants, `bench_loop` and `panda_campaign`.
- [ ] **Step 4: Run the full suite**
  - Run: `python3 tools/build_notebook.py && python3 -m unittest discover -s tests -t .`
  - Expected: `OK`.
- [ ] **Step 5: Commit**: `feat: benchmark v2 in runs/bench2: drop coord, random 3 seeds, hinted variant`.

### Task 3: Move finished hinted runs from runs/bench to runs/bench2

**Files:**
- Create: `tools/migrate_hinted.py`.
- Test: `tests/test_migrate_hinted.py`.

**Interfaces:**
- Produces: `migrate(old_root: Path, new_root: Path, apply: bool) -> list[tuple[str, str]]`, returning (source, destination) pairs as POSIX paths relative to the repo's parent folders. It moves:
  - every `old_root/<spec>/full/seed<n>/` that has `outcome.json` and whose destination `new_root/<spec>/hinted/seed<n>/` does not exist;
  - the matching log `old_root/<spec>-full-seed<n>.log` to `new_root/<spec>-hinted-seed<n>.log`, when it exists.

  In each moved run, `run_meta.json` gets `"label": "hinted"` and `"migrated_from": "<old path>"`. Without `apply`, nothing is touched and the same list is returned.
- CLI: `python3 tools/migrate_hinted.py [--old runs/bench] [--new runs/bench2] [--apply]`. It prints one line per move and a total.

- [ ] **Step 1: Write the failing tests** (build fake run folders in a temp dir with `run_meta.json` `{"label": "full", "spec": "P1"}` and an `outcome.json`; a `--fake` run from `run_mod.main` as in `BenchmarkTest` is better, so `aggregate` reads real files):
  - `test_dry_run_touches_nothing`: the list has 1 pair, and the source still exists.
  - `test_apply_moves_finished_runs_and_relabels`:
    - after `apply=True`, `aggregate(new_root)` gives one row with `variant == "hinted"` and `spec == "P1"`;
    - the source folder is gone;
    - the log has moved.
  - `test_unfinished_run_stays`: a seed folder without `outcome.json` is not moved.
  - `test_second_run_moves_nothing`: a second `migrate(..., apply=True)` returns `[]`.
  - `test_other_variants_untouched`: `old_root/P1/no_screen/seed1` stays where it is.
- [ ] **Step 2: Run and confirm they fail**
  - Run: `python3 -m unittest tests.test_migrate_hinted`
  - Expected: ImportError / ModuleNotFoundError.
- [ ] **Step 3: Implement** `tools/migrate_hinted.py` with `shutil.move` and `json` read/write of `run_meta.json`.
- [ ] **Step 4: Run the full suite**
  - Run: `python3 -m unittest discover -s tests -t .`
  - Expected: `OK`.
- [ ] **Step 5: Commit**: `feat: migrate finished hinted-prompt bench runs into runs/bench2/<spec>/hinted`.

### Task 4: Notebook task "bench2", status, publish; docs

**Files:**
- Modify: `tools/build_sync_notebook.py`:
  - `TASK_MD`:
    - remove the `"neutral"` and `"bench"` entries;
    - add `"bench2"` with this text: stops the old `piezo-bench-p*` jobs, moves their finished `full` runs to the `hinted` variant, then submits 5 jobs; 5 specs x (4 variants x 5 seeds + random x 3) = 115 runs, about 18 of them already done through migration. It says to run this right after cell 1 pulls the new code.
  - `TASK`: the `"neutral"` branch is replaced by `"bench2"`, which:
    1. reads `runs/jobs.jsonl` and calls `cancel(job)` for each entry whose `name` is exactly `piezo-bench-p1`..`piezo-bench-p5`, printing each;
    2. runs `tools/migrate_hinted.py --apply`;
    3. calls `tools.panda_campaign.main(["--cwd", str(REPO), "--bench"])`.
  - The `"bench"` branch stays only as an alias of `"bench2"` (no old layout).
  - `STATUS`: prints `benchmark v2: <n> of 115 runs finished` from `runs/bench2/*/*/seed*/outcome.json`.
  - `PUBLISH`: aggregates `runs/bench2` (not `runs/bench`) with `--bench`.
- Modify: `README.md`:
  - the benchmark section names `runs/bench2`, the variants and seeds;
  - the leakage paragraph says that neutral is the default, `hinted` is the old prompt, and the P1 campaign (`runs/exp`) used the hinted prompt.
- Modify: `CLAUDE.md`: workflow step 3b commands use `runs/bench2`.
- Test: `tests/test_notebook.py`.

- [ ] **Step 1: Write the failing test**: `SyncBench2TaskTest`.
  - `TASK` contains:
    - `'TASK == "bench2"'`;
    - `"migrate_hinted.py"`;
    - `"jobs.jsonl"`;
    - `"piezo-bench-p"`;
    - `'"--bench"'`.
  - `TASK` does not contain `'TASK == "neutral"'`.
  - `STATUS` contains `"runs/bench2"` and `"115"`.
  - `PUBLISH` contains `"runs/bench2"`.
  - Delete `SyncNeutralTaskTest`.
- [ ] **Step 2: Run and confirm it fails**
  - Run: `python3 -m unittest tests.test_notebook`
  - Expected: FAIL on `bench2`.
- [ ] **Step 3: Implement** the notebook strings and the README and CLAUDE.md edits, then `python3 tools/build_sync_notebook.py`.
- [ ] **Step 4: Full suite and a dry run**
  - Run: `python3 -m unittest discover -s tests -t .` (expected `OK`).
  - Run: `python3 -m piezo_synth.run --fake --spec P3 --out <scratchpad>/dry`. Expected: `llm/iter-01-1.json` has no `pi*sqrt`.
- [ ] **Step 5: Commit**: `feat: notebook task bench2 (stop old bench, migrate hinted runs, submit); docs`.
