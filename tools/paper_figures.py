"""Draw the paper's two figures from a campaign folder (needs matplotlib, no pandas).

    python3 tools/paper_figures.py runs/exp paper/generated

fig_variants.pdf: simulations to the first design meeting the search specification, one dot per seed;
                  runs that never met it are drawn at the number of simulations they used, as crosses.
fig_progress.pdf: best number of search conditions passed against simulations, for every seed of the
                  full method and of the variant without the screen.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from piezo_synth.experiments import VARIANT_ORDER  # noqa: E402

N_COND = 6


def _runs(root: Path):
    with (root / "experiments.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _progress(run: Path):
    """(simulations, best conditions passed so far) after every evaluated candidate."""
    xs, ys, best = [], [], 0
    for line in (run / "events.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("kind") != "candidate" or e.get("origin") == "reference":
            continue
        best = max(best, int(e.get("cond_pass") or 0))
        xs.append(int(e.get("n_sims") or 0))
        ys.append(best)
    return xs, ys


def main(argv=None) -> int:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    argv = sys.argv[1:] if argv is None else argv
    root, out = Path(argv[0]), Path(argv[1])
    out.mkdir(parents=True, exist_ok=True)
    rows = _runs(root)
    plt.rcParams.update({"font.size": 8, "font.family": "serif"})

    variants = [v for v in VARIANT_ORDER + ["audit"] if any(r["variant"] == v for r in rows)]
    fig, ax = plt.subplots(figsize=(3.5, 2.7))
    for i, v in enumerate(variants):
        rs = [r for r in rows if r["variant"] == v]
        for j, r in enumerate(rs):
            x = i + (j - (len(rs) - 1) / 2) * 0.08
            if r["met_search"] == "True":
                ax.scatter(x, float(r["first_met_sims"]), s=14, color="#1f4e79",
                           marker="o" if r["met_all"] != "True" else "D")
            else:
                ax.scatter(x, float(r["n_sims"]), s=18, color="#b03a2e", marker="x")
    ax.set_yscale("log")
    ax.set_xticks(range(len(variants)))
    ax.set_xticklabels([v.replace("_", " ") for v in variants], rotation=35, ha="right")
    ax.set_ylabel("simulations to first success")
    ax.scatter([], [], s=14, color="#1f4e79", marker="o", label="met search set")
    ax.scatter([], [], s=14, color="#1f4e79", marker="D", label="met search + held-out")
    ax.scatter([], [], s=18, color="#b03a2e", marker="x", label="never met (sims used)")
    ax.legend(fontsize=6, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, frameon=False, handletextpad=0.2, columnspacing=0.8)
    ax.grid(axis="y", lw=0.3, alpha=0.5)
    fig.tight_layout()
    fig.savefig(out / "fig_variants.pdf")
    fig.savefig(out / "fig_variants.png", dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(3.5, 2.2))
    for v, color in (("full", "#1f4e79"), ("no_screen", "#c17d11")):
        first = True
        for r in (r for r in rows if r["variant"] == v):
            xs, ys = _progress(root / v / Path(r["run"]).name)
            if xs:
                ax.step(xs, ys, where="post", color=color, lw=1, alpha=0.8, marker=".", ms=3,
                        label=v.replace("_", " ") if first else None)
                first = False
    ax.set_xscale("log")
    ax.set_ylim(-0.3, N_COND + 0.3)
    ax.set_xlabel("simulations (incl. screen runs)")
    ax.set_ylabel("best search conditions passed")
    ax.legend(fontsize=7, frameon=False, loc="lower right")
    ax.grid(lw=0.3, alpha=0.5)
    fig.tight_layout()
    fig.savefig(out / "fig_progress.pdf")
    fig.savefig(out / "fig_progress.png", dpi=200)
    plt.close(fig)
    print(f"figures written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
