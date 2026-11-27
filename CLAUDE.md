# Working on this repository on Panda (CAIR, Memorial University)

Note (2026-11-27): Panda blocks claude.ai and api.anthropic.com, so this file applies only if that changes.
Meanwhile the code runs on Panda through `panda_sync.ipynb`, which publishes light results to the
`results` branch; read them with `git fetch origin results` and `git show origin/results:<path>`.

This repository synthesises piezoelectric energy-harvesting interface circuits: Gemma 4 31B proposes
circuit structures, LTspice simulates them, a power screen and an evolution-strategy sizer refine them.
`README.md` explains the method, the spec and every output file; `paper/` is the paper, whose results
tables are generated from the runs. Read `README.md` before your first task.

The person you work for writes in Vietnamese: answer in Vietnamese. Code, commit messages and
documentation stay in English.

## Where you are

- You run in the **terminal of the team's JupyterLab on Panda**. The terminal is not a compute node:
  it has about 4 GB of memory **shared with the whole team's notebook kernels**, no GPU and no LTspice.
- Only **`/work` persists**; it is shared by the whole team (50 GB in total). This repository lives in
  the person's own folder under `/work`. Everything outside `/work` is lost when the notebook restarts.
- Gemma is served inside the cluster at the URL in `piezo_synth/llm.py`; only Panda jobs and the
  notebook can reach it.
- LTspice runs only inside jobs on the `ltspice-cpu` image (Wine, batch mode, `/opt/ltspice/ltspice_run.py`).

## Hard rules

1. **Never run simulations, searches or the test bench in the terminal.** Every `piezo_synth.run`,
   `piezo_synth.reproduce` or anything that calls LTspice or Gemma goes into a job:
   `python3 tools/panda_submit.py --name <short-name> -- "<command>"` (run from the repository folder).
   Light work is fine in the terminal: reading files, `git`, editing code, unit tests,
   `python3 -m piezo_synth.report runs/<id>`, `python3 -m piezo_synth.experiments runs/exp`.
2. **Stay inside this repository's folder.** Do not read, change or delete anything in other people's
   folders under `/work`, and never cancel a job you did not submit (yours are listed in `runs/jobs.jsonl`).
3. **Ask before deleting runs** (`runs/...`), before `git push`, before force operations, and before
   anything that would take the team's GPU (these jobs use `gpus=0`; keep it that way).
4. **Secrets:** never print, copy, commit or log tokens, passwords or credentials (GitHub token,
   Claude login, anything in `$HOME`). If a command would display one, don't run it.
5. **One LTspice job at a time by default.** All jobs share the Wine prefix `/work/.wine-ltspice`;
   the campaign submits several at once, which is allowed only after a smoke test and one single run
   have worked. If Wine errors appear in `sims/*/*.log` (`wineserver`, `prefix`), resubmit variants one
   by one instead.

## Submitting and following jobs

```bash
python3 tools/panda_submit.py --name piezo-smoke -- \
  "rm -rf runs/smoke && python3 -u -m piezo_synth.run --smoke --out runs/smoke"
```

It runs in this folder on `/work` (same files), image `ltspice-cpu`, no GPU, 8 CPUs, 16 GiB, 4 h by
default (`--timeout` seconds, `--cpus`, `--memory`). The command may not contain single quotes. The
output also goes to `runs/logs/<name>.log`, because the cluster deletes job logs 48 h after a job ends.

Jobs take minutes (smoke) to hours (campaign). **Do not block on them**: tool calls time out. Submit,
then check in with short commands:

- `tail -n 30 runs/logs/<name>.log`: the job's console output (phase tags `[model]`, `[screen]`,
  `[sim]`, `[size]`, `[heldout]`, `[robust]`, `[done]`).
- `cat runs/<run>/progress.json`: phase, round, simulations, best design so far.
- `python3 -c "from gpu import jobs; jobs()"`: status of the team's jobs (0/1 with no pod = waiting
  for resources, which is normal).
- `python3 -c "from gpu import cancel; cancel('<job-name>')"`: stop one of **your** jobs.

## The workflow

1. **Smoke test** (about 2 min, 26 simulations): command above. Then check `runs/logs/piezo-smoke.log`
   against README "First run (smoke test checklist)": the reference fails several search
   conditions, the witness passes them, `t_up` values are crossing times, the screen powers of the
   reference are positive and the witness passes the screen. Device models changed after the first
   Panda runs, so earlier smoke results are out of date.
2. **One single run**: `python3 tools/panda_submit.py --name piezo-run -- "python3 -u -m piezo_synth.run
   --out runs/single-$(date +%Y%m%d-%H%M%S)"` (defaults from `SearchConfig`; pass `--config file.json`
   to change them). Read `runs/<id>/report.md` when it finishes.
3. **Campaign** for the paper: `python3 tools/panda_campaign.py` (8 variants x 5 seeds, one job per
   variant, resumable). Progress: `ls runs/exp/*/seed*/outcome.json | wc -l` (40 when done).
3b. **Benchmark** (P1-P5, README "The benchmark of specifications"): first
   `python3 tools/panda_submit.py --name piezo-speccheck -- "python3 -u -m piezo_synth.speccheck --out runs/speccheck"`,
   read `runs/speccheck/speccheck.md`, drop or relax unproven specs, then the notebook task `"bench2"` (stops
   the old `piezo-bench-p*` jobs, `tools/migrate_hinted.py --apply`, `python3 tools/panda_campaign.py --bench`:
   `runs/bench2`, one job per spec, 115 runs, neutral prompt; the `hinted` variant is the original prompt).
   Aggregate with `python3 -m piezo_synth.experiments runs/bench2 --bench --paper paper/generated`.
4. **Aggregate**: `python3 -m piezo_synth.experiments runs/exp --paper paper/generated --smoke runs/smoke`
   writes `runs/exp/experiments*.csv` and the paper's tables. The two figures of the paper are drawn by
   the notebook's Aggregate cell (matplotlib); you may run the same code with `python3` in the terminal.
5. **Paper**: write the paragraphs marked `\pending{...}` in `paper/main.tex` from the generated tables
   only. Claim a difference between variants only where the seeds support it, and report the spread.
   Never type a number into the paper that is not in `paper/generated/` or a run folder.

## Changing code

- Tests: `python3 -m unittest discover -s tests -t .` (pytest may not be installed here). They use
  fakes for LTspice and Gemma, so they run in the terminal in seconds. Keep them green; add a test that
  fails first for every bug you fix.
- After any change in `piezo_synth/`, run `python3 tools/build_notebook.py` (the notebook embeds the
  package; `tests/test_notebook.py` fails if it is stale).
- Dry run of the whole pipeline without LTspice or Gemma: `python3 -m piezo_synth.run --fake --out /tmp/dry`
  (in `/tmp`, not `runs/`; its numbers are not circuit simulations).
- Work on branch `feat/v2-screen-size-paper` unless told otherwise. Commit with clear messages; push only
  when the person asks.

## Debugging simulations

- Every simulation's netlist and LTspice log are in `runs/<run>/sims/<hash>/` (`circuit.net`, `*.log`).
- `measurements.csv` and `checks.csv` in a run folder hold every number behind a pass/fail decision.
- Known open points to verify on the first real runs: the sign of the screen measurement
  (`V(out,vsn)`, the smoke test warns), where `ltspice_run` writes `.raw` files (the waveform job prints a
  WARNING listing the folder if it finds none), and whether `ltspice_run` parses `FIND ... WHEN` results.
