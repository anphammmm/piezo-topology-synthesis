"""Generate piezo_synth.ipynb: one notebook that writes the package (%%writefile), runs the job and
analyses the results. Run after any change to piezo_synth/:  python tools/build_notebook.py"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MODULE_ORDER = ["__init__", "spec", "circuit", "netlist", "sim", "evaluate", "bench", "screen", "sizer",
                "diagnostics", "robust", "llm", "baselines", "prompts", "refine", "records", "search", "report",
                "experiments", "rawread", "run", "reproduce"]

INTRO = """# AI-assisted topology synthesis: piezoelectric energy-harvester interface

Gemma 4 31B proposes interface-circuit **structures** for a piezoelectric harvester, up to three per
round. Each new structure goes through three stages:
1. **Screen** (cheap, about 1/8 of a full evaluation): the storage node is fixed at 1.8 V and the net
   power the circuit delivers is measured on the three hardest conditions, for the proposed values
   and a few automatic presets (e.g. LC-resonant switch timing). A structure that cannot deliver at
   least half of the load's need is sent back with its powers and is not tuned.
2. **Full evaluation**: 0.8 s cold-start LTspice runs on the six search conditions.
3. **Sizing**: an evolution strategy tunes all component values (up to 48 evaluations per
   structure), running while Gemma thinks about the next round.

Feedback to Gemma includes measurements, screen powers and plain-language diagnoses (e.g. "the
output never exceeds 0.7 V: check diode orientations"). When the search stops, the selected design
and the full-bridge reference are checked on four **held-out** conditions that the model never saw,
and the selected design gets a Monte Carlo robustness check (component tolerances, switch timing).

**Specification (every condition, 0.8 s cold start):** output reaches and stays at 1.8 V or more,
never exceeds 3.6 V, ripple at most 50 mV, reaches 1.8 V within 0.4 s, settled. Conditions vary
the load (150 kOhm to 2.2 MOhm), excitation (30-100 uA), frequency (80 Hz), piezo capacitance (+20 %)
and temperature (60 C). See section 1 of `report.md` once a run finishes.

**Run the cells in order:**
1. *Setup* (always).
2. *Package files*: writes `piezo_synth/` next to this notebook (always, after any update of this notebook).
3. *Settings* for the search.
4. *Smoke test* (first time, and after any change to the device models; about 2 minutes).
5. *Single run* (typically 30-60 minutes): one cluster job; `log()` follows it, `cancel(job)` stops it.
6. *Progress* (any time), *Results*, *Figures*, *Waveforms*.
7. *Experiment campaign* (for the paper): all variants x seeds as cluster jobs, then *Aggregate*,
   which writes the paper's tables and figures into `paper_generated/`.

Progress lines are tagged by phase: `[model]` waiting for Gemma, `[screen]` power screen, `[sim]`
simulating, `[eval]` checking results, `[size]` value sizing, `[heldout]` held-out check,
`[robust]` Monte Carlo, `[done]`.
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

- `max_rounds`: model calls at most (each ~1-4 min with thinking on); `proposals_per_round`: designs per call.
- `min_rounds`: the model may only declare itself done (and stagnation may only stop the run) after this many.
- `wall_clock_s`, `max_sims`: time and simulation budgets (0 = no simulation budget).
- `stagnation`: stop after this many rounds without improving the best proposed design.
- `screen`, `screen_presets`, `screen_alpha`: the power screen (alpha = fraction of the load's need required).
- `sizer` (`es`, `coord` or `none`), `size_budget`, `size_lambda`: value sizing.
- `diagnostics`: plain-language diagnoses in the feedback.
- `mc_samples`: Monte Carlo samples for the selected design.
- `think`: Gemma reasoning on (recommended); `seed`: random seed for screen presets and sizing."""

SETTINGS = '''CONFIG = dict(max_rounds=12, min_rounds=3, proposals_per_round=3, wall_clock_s=3600, max_sims=3000,
              stagnation=5, screen=True, screen_presets=4, screen_alpha=0.5, sizer="es", size_budget=48,
              size_lambda=8, diagnostics=True, mc_samples=16, think=True, seed=1)
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

FULL_MD = """## 5. Single run

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
print(f"phase: {p.get('phase')}   round {p.get('iteration')}/{p.get('max_rounds')}   "
      f"simulations {p.get('n_sims')}   elapsed {p.get('elapsed_s', 0) / 60:.1f} min")
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

# 1. score over the search, proposals coloured by move, sizing steps in grey
fig, ax = plt.subplots(figsize=(8, 4))
search["order"] = range(len(search))
best = search.scalar.cummax()
ax.plot(search.order, best, "k-", lw=1.5, label="best so far")
colours = {"new_topology": "tab:blue", "modify_topology": "tab:orange", "resize": "tab:green",
           "size": "lightgrey", "refine": "lightgrey", "audit": "wheat", "reference": "tab:red"}
for mv, grp in search.groupby("move"):
    small = mv in ("size", "refine", "audit")
    ax.scatter(grp.order, grp.scalar, s=10 if small else 25, c=colours.get(mv, "k"), label=mv, zorder=2 if small else 3)
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

missing = []
fig, axes = plt.subplots(1, 2, figsize=(11, 3.6), sharey=True)
for ax, cond in zip(axes, ["S1", "S4"]):
    for lab in ("selected", "reference"):
        info_file = RUN / f"waves-{lab}" / "reproduce.json"
        if not info_file.exists():
            missing.append(f"{lab}: {info_file} not found (has the Waveforms job finished? see log(wave))")
            continue
        raw = json.loads(info_file.read_text())["raw_files"].get(cond)
        if not raw:
            missing.append(f"{lab} {cond}: no .raw file was produced (see the WARNING lines in log(wave))")
            continue
        d = read_raw(raw)
        key = next((k for k in d if k.lower() == "v(out)"), None)
        if key is None:
            missing.append(f"{lab} {cond}: V(out) not in {raw}; signals: {list(d)[:8]}")
            continue
        ax.plot(d["time"], d[key], lw=0.8, label=lab)
    for v in (1.8, 3.6):
        ax.axhline(v, color="k", ls="--", lw=0.6)
    ax.set(title=cond, xlabel="time, s", ylabel="V(out), V")
    if ax.get_legend_handles_labels()[0]:
        ax.legend()
fig.tight_layout(); fig.savefig(figdir / "waveforms.png", dpi=200); fig.savefig(figdir / "waveforms.pdf")
for m in missing:
    print("MISSING:", m)'''

CAMPAIGN_MD = """## 7. Experiment campaign (for the paper)

Every variant runs the same seeds with the same simulation budget (`max_sims`), so variants are
compared by **simulations used**, which does not depend on how busy the shared Gemma server is.

| variant | what changes |
|---|---|
| `full` | the method as described above |
| `no_screen` | no power screen: every structure is evaluated in full and sized |
| `no_diag` | no plain-language diagnoses in the feedback (tables only) |
| `single` | one design per round instead of three |
| `coord` | the earlier coordinate-search tuner instead of the evolution strategy |
| `no_think` | Gemma's reasoning turned off |
| `random` | no model: random valid circuits through the same screen and sizing |
| `audit` | like `full`, but screen-rejected structures are also sized (measures how often the screen is wrong) |

One cluster job per variant runs its seeds one after another. With 5 seeds a variant takes up to
about 5 hours; all variants run at the same time. Re-running a variant skips seeds already finished."""

CAMPAIGN = '''SEEDS = [1, 2, 3, 4, 5]
BASE = dict(CONFIG, max_sims=3000, wall_clock_s=3600, mc_samples=16)
VARIANTS = {
    "full": ({}, ""),
    "no_screen": ({"screen": False}, ""),
    "no_diag": ({"diagnostics": False}, ""),
    "single": ({"proposals_per_round": 1, "max_rounds": 24}, ""),
    "coord": ({"sizer": "coord"}, ""),
    "no_think": ({"think": False}, ""),
    "random": ({}, "--baseline random"),
    "audit": ({"screen_audit": True}, ""),
}
os.makedirs("runs/exp", exist_ok=True)
campaign = {}
for name, (over, extra) in VARIANTS.items():
    Path(f"runs/exp/{name}.json").write_text(json.dumps(dict(BASE, **over), indent=1))
    loop = " ; ".join(
        f"( test -f runs/exp/{name}/seed{s}/outcome.json || python3 -u -m piezo_synth.run --config runs/exp/{name}.json "
        f"--label {name} --seed {s} {extra} --out runs/exp/{name}/seed{s} > runs/exp/{name}-seed{s}.log 2>&1 )"
        for s in SEEDS)
    campaign[name] = run(f"bash -c '{loop}'", image=LTSPICE, gpus=0, cpus=8, memory="16Gi",
                         timeout=12 * 3600, name=f"piezo-{name.replace('_', '-')}")
    print("submitted", name, campaign[name])'''

CAMPAIGN_STATUS = '''# how far each variant has got (safe to run any time)
for name in VARIANTS:
    done = sorted(glob.glob(f"runs/exp/{name}/seed*/outcome.json"))
    print(f"{name:<10} {len(done)}/{len(SEEDS)} seeds finished")'''

AGGREGATE_MD = """### Aggregate and write the paper's tables

Writes `runs/exp/experiments.csv` (one row per run), `runs/exp/experiments_summary.csv` (one row per
variant) and the LaTeX tables in `paper_generated/`. Download that folder into the repository's
`paper/generated/` and compile `paper/main.tex`; every number in the paper's results comes from it."""

AGGREGATE = '''import pandas as pd
import matplotlib.pyplot as plt
from piezo_synth.experiments import aggregate, write_paper_tables

runs_, summary_ = aggregate("runs/exp")
write_paper_tables("paper_generated", "runs/exp", smoke="runs/smoke")
df = pd.DataFrame(runs_); sm = pd.DataFrame(summary_)
display(sm)
figdir = Path("paper_generated"); figdir.mkdir(exist_ok=True)
order = [v for v in ["full", "no_screen", "no_diag", "single", "coord", "no_think", "random", "audit"] if v in set(df.variant)]
fig, axes = plt.subplots(1, 2, figsize=(10, 3.4))
axes[0].bar(order, [sm.set_index("variant").success_rate.get(v, 0) * 100 for v in order], color="tab:blue")
axes[0].set(ylabel="runs meeting the spec (%)", ylim=(0, 100))
data = [df[(df.variant == v) & df.met_search].first_met_sims.dropna().values for v in order]
axes[1].boxplot(data, labels=order); axes[1].set(ylabel="simulations to first success")
for ax in axes:
    ax.tick_params(axis="x", rotation=30)
fig.tight_layout(); fig.savefig(figdir / "fig_variants.pdf"); fig.savefig(figdir / "fig_variants.png", dpi=200)
# search progress of the first successful full run, for the paper
ok = df[(df.variant == "full") & df.met_search]
if len(ok):
    run_dir = Path(ok.iloc[0].run)
    c = pd.read_csv(run_dir / "candidates.csv"); c = c[c.split == "search"].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(c.index, c.scalar.cummax(), "k-", lw=1.2, label="best so far")
    for mv, g in c.groupby("move"):
        ax.scatter(g.index, g.scalar, s=6 if mv in ("size", "audit") else 18, label=mv)
    ax.set(xlabel="design evaluated", ylabel="score"); ax.legend(fontsize=7, ncol=2)
    fig.tight_layout(); fig.savefig(figdir / "fig_progress.pdf")
import shutil; shutil.make_archive("paper_generated", "zip", "paper_generated")
print("download paper_generated.zip and unpack it into paper/generated/")'''


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
              code(WAVES_PLOT), md(CAMPAIGN_MD), code(CAMPAIGN), code(CAMPAIGN_STATUS), md(AGGREGATE_MD),
              code(AGGREGATE)]
    nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python",
                                                      "name": "python3"},
                                       "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    Path(out).write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    build()
    print("wrote", ROOT / "piezo_synth.ipynb")
