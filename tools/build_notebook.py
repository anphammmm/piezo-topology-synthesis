"""Generate piezo_synth.ipynb: one notebook that writes the package (%%writefile), runs the job and
analyses the results. Run after any change to piezo_synth/:  python tools/build_notebook.py"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MODULE_ORDER = ["__init__", "spec", "circuit", "netlist", "sim", "evaluate", "llm", "prompts", "refine",
                "records", "search", "report", "rawread", "run", "reproduce"]

INTRO = """# AI-assisted topology synthesis: piezoelectric energy-harvester interface

Gemma 4 31B proposes interface circuits (connectivity **and** component values) for a piezoelectric
harvester; LTspice simulates each one under six operating conditions; the measurements are checked
against a fixed specification and fed back for the next proposal. Between model calls, a numerical
optimiser tunes the component values of the most promising design. When the search stops, the
selected design and the full-bridge-rectifier reference are checked on four **held-out** conditions
that the model never saw.

**Specification (every condition, 0.8 s cold start):** output reaches and stays at 1.8 V or more,
never exceeds 3.6 V, ripple at most 50 mV, reaches 1.8 V within 0.4 s, settled. Conditions vary
the load (150 kOhm to 2.2 MOhm), excitation (30-100 uA), frequency (80 Hz), piezo capacitance (+20 %)
and temperature (60 C). See section 1 of `report.md` once a run finishes.

**Run the cells in order:**
1. *Setup* (always).
2. *Package files*: writes `piezo_synth/` next to this notebook (always, after any update of this notebook).
3. *Settings* for the search.
4. *Smoke test* (first time only, about 2 minutes): simulates the reference and a known-good witness
   circuit on all 10 conditions, without the model. It checks LTspice and shows how hard the spec is.
5. *Full experiment* (typically 30-60 minutes): runs as a cluster job, so you can close the laptop.
   `log()` follows its output; stopping `log()` does **not** stop the job (`cancel(job)` does).
6. *Progress* (any time), *Results*, *Figures*, *Waveforms*.

Progress lines are tagged by phase: `[model]` waiting for Gemma, `[refine]` tuning values,
`[sim]` simulating, `[eval]` checking results, `[heldout]` final held-out check, `[done]`.
"""

SETUP = '''import os, json, time, glob
from pathlib import Path
from gpu import run, log, jobs, cancel

os.makedirs("piezo_synth", exist_ok=True)
os.makedirs("runs", exist_ok=True)
NAMESPACE = open("/var/run/secrets/kubernetes.io/serviceaccount/namespace").read().strip()
LTSPICE = f"image-registry.openshift-image-registry.svc:5000/{NAMESPACE}/ltspice-cpu:latest"
RUN_ID = time.strftime("%Y%m%d-%H%M%S")   # re-run this cell for a new run id
print("LTspice image:", LTSPICE)
print("this run will write to runs/" + RUN_ID)'''

FILES_MD = """## 2. Package files

The next cells write the experiment's code into `piezo_synth/` beside this notebook (cells are
collapsed; expand to read). The job reads them from there. The specification lives in
`piezo_synth/spec.py`."""

SETTINGS_MD = """## 3. Settings

- `max_proposals`: model proposals at most (each ~0.5-2.5 min with thinking on).
- `min_proposals`: the model may only declare itself done after this many.
- `wall_clock_s`: stop starting new proposals after this many seconds.
- `stagnation`: stop after this many proposals without improving the best score.
- `refine_budget`: value-tuning evaluations per tuning pass (each = 6 parallel simulations).
- `think`: Gemma reasoning on for proposals (recommended).
- `seed`: random seed for the value tuner (the model itself is not deterministic)."""

SETTINGS = '''CONFIG = dict(max_proposals=16, min_proposals=4, wall_clock_s=3600, stagnation=6,
              refine_budget=10, refine_min=3, think=True, seed=1)
Path("run_config.json").write_text(json.dumps(CONFIG, indent=1))
CONFIG'''

SMOKE_MD = """## 4. Smoke test (first run only)

Expect: 20 simulations, `[sim]`/`[eval]` lines and two tables per circuit. Check that the reference
**fails** several search conditions (that is what makes the spec challenging) and that the witness
passes more of them. If the job prints a WARNING about `P_ext`, read the README section "First run"."""

SMOKE = '''smoke = run("bash -o pipefail -c 'rm -rf runs/smoke && mkdir -p runs && python3 -u -m piezo_synth.run --smoke --out runs/smoke "
            "2>&1 | tee runs/smoke.log'",
            image=LTSPICE, gpus=0, cpus=8, memory="16Gi", timeout=3600, name="piezo-smoke")
log(smoke)'''

FULL_MD = """## 5. Full experiment

One CPU job runs everything: Gemma calls (served on the cluster's GPUs), LTspice simulations in 8
parallel threads, value tuning while Gemma thinks, the held-out check and the report. The console
output is also saved to `runs/<RUN_ID>.log` (the job's own log is deleted after 48 hours)."""

FULL = '''job = run(f"bash -o pipefail -c 'mkdir -p runs && python3 -u -m piezo_synth.run --config run_config.json "
          f"--out runs/{RUN_ID} 2>&1 | tee runs/{RUN_ID}.log'",
          image=LTSPICE, gpus=0, cpus=8, memory="16Gi", timeout=4 * 3600, name="piezo-synth")
print("submitted", job, "-> runs/" + RUN_ID)
log(job)'''

PROGRESS_MD = """## 6. Progress, results, figures

To look at an earlier run, set `RUN_ID` to its folder name under `runs/` first."""

PROGRESS = '''RUN = Path("runs") / RUN_ID
p = json.loads((RUN / "progress.json").read_text()) if (RUN / "progress.json").exists() else {}
print(f"phase: {p.get('phase')}   proposal {p.get('iteration')}/{p.get('max_proposals')}   "
      f"elapsed {p.get('elapsed_s', 0) / 60:.1f} min")
print(f"best so far: {p.get('best_id')} {p.get('best_name')!r}  score {p.get('best_scalar')}  "
      f"conditions passed {p.get('best_cond_pass')}/6")
if p.get("phase") == "model":
    print(f"waiting for the model for {p.get('model_wait_s', 0)} s")
if p.get("stop_reason"):
    print("stop reason:", p["stop_reason"])'''

RESULTS = '''import pandas as pd
from IPython.display import Markdown, display
from piezo_synth.report import build_report

build_report(RUN)          # refresh (also works on an unfinished or killed run)
display(Markdown((RUN / "report.md").read_text()))
cands = pd.read_csv(RUN / "candidates.csv")
meas = pd.read_csv(RUN / "measurements.csv")
checks = pd.read_csv(RUN / "checks.csv")
summary = json.loads((RUN / "summary.json").read_text())
SEL, REF = summary["selected_id"], summary["reference_id"]
cands.head()'''

FIGURES = '''import matplotlib.pyplot as plt
import numpy as np
from piezo_synth import spec

figdir = RUN / "figures"; figdir.mkdir(exist_ok=True)
search = cands[cands.split == "search"].copy()

# 1. score over the search, proposals coloured by move, tuning steps in grey
fig, ax = plt.subplots(figsize=(8, 4))
search["order"] = range(len(search))
best = search.scalar.cummax()
ax.plot(search.order, best, "k-", lw=1.5, label="best so far")
colours = {"new_topology": "tab:blue", "modify_topology": "tab:orange", "resize": "tab:green",
           "refine": "lightgrey", "reference": "tab:red"}
for mv, grp in search.groupby("move"):
    ax.scatter(grp.order, grp.scalar, s=25 if mv != "refine" else 10, c=colours.get(mv, "k"), label=mv, zorder=3)
ax.set(xlabel="design evaluated (in order)", ylabel="score", title="Search progress")
ax.legend(fontsize=8, ncol=3); fig.tight_layout()
fig.savefig(figdir / "search_progress.png", dpi=200); fig.savefig(figdir / "search_progress.pdf")

# 2. pass/fail map: selected vs reference, all conditions x criteria
conds = [c.id for c in spec.CONDITIONS]; crits = [c.id for c in spec.CRITERIA]
fig, axes = plt.subplots(1, 2, figsize=(11, 3.6), sharey=True)
for ax, (cid, title) in zip(axes, [(SEL, f"selected ({SEL})"), (REF, f"reference ({REF})")]):
    sub = checks[checks.candidate == cid]
    grid = np.full((len(crits), len(conds)), np.nan)
    for _, r in sub.iterrows():
        grid[crits.index(r.criterion), conds.index(r.condition)] = 1.0 if str(r.passed) == "True" else 0.0
    ax.imshow(grid, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(conds)), conds); ax.set_yticks(range(len(crits)), crits); ax.set_title(title)
    ax.axvline(5.5, color="k", lw=1)          # left: search conditions, right: held-out
fig.suptitle("green = pass, red = fail; conditions right of the line are held out"); fig.tight_layout()
fig.savefig(figdir / "pass_fail.png", dpi=200); fig.savefig(figdir / "pass_fail.pdf")

# 3. output voltage and load power per condition
fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
x = np.arange(len(conds)); w = 0.38
for k, (cid, lab) in enumerate([(SEL, "selected"), (REF, "reference")]):
    sub = meas[meas.candidate == cid].set_index("condition").reindex(conds)
    axes[0].bar(x + (k - 0.5) * w, sub.vavg, w, label=lab)
    axes[1].bar(x + (k - 0.5) * w, sub.pload * 1e6, w, label=lab)
for v in (1.8, 3.6):
    axes[0].axhline(v, color="k", ls="--", lw=0.8)
axes[0].set(ylabel="mean V(out), V", xticks=x, xticklabels=conds)
axes[1].set(ylabel="load power, uW", xticks=x, xticklabels=conds)
axes[0].legend(); fig.tight_layout()
fig.savefig(figdir / "vout_power.png", dpi=200); fig.savefig(figdir / "vout_power.pdf")
print("figures saved in", figdir)'''

WAVES_MD = """### Waveforms

Re-simulates the selected design and the reference on S1 and S4 with all signals saved, then plots
V(out). This is also how to reproduce any design: point `reproduce` at its `circuit.json`."""

WAVES = '''wave = run(f"python3 -u -m piezo_synth.reproduce runs/{RUN_ID}/selected/circuit.json "
           f"--out runs/{RUN_ID}/waves-selected --conditions S1,S4 --waveforms && "
           f"python3 -u -m piezo_synth.reproduce runs/{RUN_ID}/candidates/{REF}/circuit.json "
           f"--out runs/{RUN_ID}/waves-reference --conditions S1,S4 --waveforms",
           image=LTSPICE, gpus=0, cpus=4, memory="8Gi", timeout=1800, name="piezo-waves")
log(wave)'''

WAVES_PLOT = '''from piezo_synth.rawread import read_raw

fig, axes = plt.subplots(1, 2, figsize=(11, 3.6), sharey=True)
for ax, cond in zip(axes, ["S1", "S4"]):
    for lab in ("selected", "reference"):
        info = json.loads((RUN / f"waves-{lab}" / "reproduce.json").read_text())
        raw = info["raw_files"].get(cond)
        if raw:
            d = read_raw(raw)
            ax.plot(d["time"], d["V(out)"], lw=0.8, label=lab)
    for v in (1.8, 3.6):
        ax.axhline(v, color="k", ls="--", lw=0.6)
    ax.set(title=cond, xlabel="time, s", ylabel="V(out), V"); ax.legend()
fig.tight_layout(); fig.savefig(figdir / "waveforms.png", dpi=200); fig.savefig(figdir / "waveforms.pdf")'''


def _lines(text: str):
    parts = text.split("\n")
    return [p + "\n" for p in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": _lines(text)}


def code(text: str, hidden: bool = False) -> dict:
    meta = {"jupyter": {"source_hidden": True}} if hidden else {}
    return {"cell_type": "code", "execution_count": None, "metadata": meta, "outputs": [], "source": _lines(text)}


def build(out: Path = ROOT / "piezo_synth.ipynb") -> None:
    pkg = ROOT / "piezo_synth"
    names = [n for n in MODULE_ORDER if (pkg / f"{n}.py").exists()]
    names += sorted(p.stem for p in pkg.glob("*.py") if p.stem not in names)
    cells = [md(INTRO), md("## 1. Setup"), code(SETUP), md(FILES_MD)]
    for n in names:
        src = (pkg / f"{n}.py").read_text(encoding="utf-8")
        cells.append(code(f"%%writefile piezo_synth/{n}.py\n" + src, hidden=True))
    cells += [md(SETTINGS_MD), code(SETTINGS), md(SMOKE_MD), code(SMOKE), md(FULL_MD), code(FULL),
              md(PROGRESS_MD), code(PROGRESS), code(RESULTS), code(FIGURES), md(WAVES_MD), code(WAVES),
              code(WAVES_PLOT)]
    nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python",
                                                      "name": "python3"},
                                       "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    Path(out).write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    build()
    print("wrote", ROOT / "piezo_synth.ipynb")
