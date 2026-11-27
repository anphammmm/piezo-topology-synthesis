"""Submit the paper's experiment campaign from the notebook's terminal: one job per variant, each
running its seeds in turn (finished seeds are skipped, so re-running this resumes a campaign).

    python3 tools/panda_campaign.py                       # all variants, seeds 1-5
    python3 tools/panda_campaign.py --variants full,random --seeds 1,2
    python3 tools/panda_campaign.py --bench                # runs/bench2: every spec x 5 variants (random 3 seeds), one job per spec
    python3 tools/panda_campaign.py --bench --specs P2,P3
    python3 tools/panda_campaign.py --bench --variants hinted --specs P1,P3   # one extra variant, own job names

Run it from the repository folder. Then: python3 -m piezo_synth.experiments runs/exp
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # the repository, for piezo_synth

from piezo_synth import spec  # noqa: E402
from piezo_synth.experiments import BENCH_ROOT, BENCH_VARIANTS, VARIANTS, bench_loop, campaign_loop, write_campaign_configs  # noqa: E402
from tools import panda_submit  # noqa: E402

# runs/exp (the P1 campaign) used the original prompt for every variant: "hinted" would only repeat full
CAMPAIGN_VARIANTS = [v for v in VARIANTS if v != "hinted"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variants", default=",".join(CAMPAIGN_VARIANTS),
                    help=f"comma list of {', '.join(VARIANTS)} (default: {', '.join(CAMPAIGN_VARIANTS)})")
    ap.add_argument("--seeds", default="1,2,3,4,5")
    ap.add_argument("--bench", action="store_true", help="the benchmark: runs/bench2/<spec>/<variant>/seed<n>")
    ap.add_argument("--specs", default=",".join(spec.SPECS), help="with --bench: which specs")
    ap.add_argument("--image")
    ap.add_argument("--work-root", default="/work", help=argparse.SUPPRESS)
    ap.add_argument("--cwd", default=None, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    names = [v.strip() for v in a.variants.split(",") if v.strip()]
    unknown = [v for v in names if v not in VARIANTS]
    if unknown:
        ap.error(f"unknown variants: {', '.join(unknown)}")
    seeds = [int(s) for s in a.seeds.split(",") if s.strip()]
    cwd = Path(a.cwd or os.getcwd())
    if a.bench:
        custom = a.variants != ",".join(CAMPAIGN_VARIANTS)
        variants = names if custom else BENCH_VARIANTS
        # extra variants get their own job names, so they never collide with the spec's main bench job
        suffix = "".join("-" + v.replace("_", "-") for v in variants) if custom else ""
        write_campaign_configs(cwd / BENCH_ROOT)
        common = ["--work-root", a.work_root, "--cwd", str(cwd)] + (["--image", a.image] if a.image else [])
        for sp in [x.strip() for x in a.specs.split(",") if x.strip()]:
            if sp not in spec.SPECS:
                ap.error(f"unknown spec {sp}")
            panda_submit.main(common + ["--name", f"piezo-bench2-{sp.lower()}{suffix}", "--timeout", str(36 * 3600),
                                        "--", bench_loop(sp, variants, seeds, BENCH_ROOT)])
        return 0
    write_campaign_configs(cwd / "runs" / "exp")
    common = ["--work-root", a.work_root, "--cwd", str(cwd)] + (["--image", a.image] if a.image else [])
    for name in names:
        panda_submit.main(common + ["--name", f"piezo-{name.replace('_', '-')}", "--timeout", str(12 * 3600),
                                    "--", campaign_loop(name, seeds)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
