"""Free space on /work: delete the LTspice .raw waveform files left by earlier runs.

    python3 tools/clean_raw.py runs            # only reports how much would be freed
    python3 tools/clean_raw.py runs --delete   # deletes them

Measurements are already in each run's CSV files and the simulation logs, so nothing the reports or
the paper use is lost. Folders named waves-* (waveforms kept on purpose for plots) are left alone.
Newer code deletes each .raw as soon as its simulation is measured, so this is needed only once.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def clean(root, delete: bool):
    n = size = 0
    for f in Path(root).rglob("*.raw"):
        if any(part.startswith("waves-") for part in f.parts):
            continue
        try:
            s = f.stat().st_size
            if delete:
                f.unlink()
        except OSError:
            continue
        n += 1
        size += s
    return n, size


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", default="runs")
    ap.add_argument("--delete", action="store_true", help="actually delete (default: only report)")
    a = ap.parse_args(argv)
    n, size = clean(a.root, a.delete)
    verb = "deleted" if a.delete else "would delete (add --delete to do it)"
    print(f"{verb}: {n} .raw files, {size / 2**30:.2f} GiB under {a.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
