"""Submit the paper's experiment campaign from the notebook's terminal: one job per variant, each
running its seeds in turn (finished seeds are skipped, so re-running this resumes a campaign).

    python3 tools/panda_campaign.py                       # all variants, seeds 1-5
    python3 tools/panda_campaign.py --variants full,random --seeds 1,2

Run it from the repository folder. Then: python3 -m piezo_synth.experiments runs/exp
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # the repository, for piezo_synth

from piezo_synth.experiments import VARIANTS, campaign_loop, write_campaign_configs  # noqa: E402
from tools import panda_submit  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variants", default=",".join(VARIANTS), help=f"comma list of {', '.join(VARIANTS)}")
    ap.add_argument("--seeds", default="1,2,3,4,5")
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
    write_campaign_configs(cwd / "runs" / "exp")
    common = ["--work-root", a.work_root, "--cwd", str(cwd)] + (["--image", a.image] if a.image else [])
    for name in names:
        panda_submit.main(common + ["--name", f"piezo-{name.replace('_', '-')}", "--timeout", str(12 * 3600),
                                    "--", campaign_loop(name, seeds)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
