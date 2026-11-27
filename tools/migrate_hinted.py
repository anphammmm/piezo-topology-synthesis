"""Move the finished runs of the first benchmark's `full` variant (which used the original, hinted prompt)
into benchmark v2 as the `hinted` variant, so they are not run again.

    python3 tools/migrate_hinted.py                 # show what would move
    python3 tools/migrate_hinted.py --apply         # move runs/bench/<spec>/full/seed<n> -> runs/bench2/<spec>/hinted/seed<n>

Only finished runs (with outcome.json) move; a destination that exists is never overwritten; nothing is
deleted. Each moved run's run_meta.json gets label "hinted" and "migrated_from". Run it from the
repository folder, after the old benchmark jobs have stopped.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import List, Tuple

SEED = re.compile(r"seed(\d+)$")


def migrate(old_root: Path, new_root: Path, apply: bool) -> List[Tuple[str, str]]:
    old_root, new_root = Path(old_root), Path(new_root)
    moves = []
    for outcome in sorted(old_root.glob("*/full/seed*/outcome.json")):
        src = outcome.parent
        m = SEED.match(src.name)
        if not m:
            continue
        spec = src.parent.parent.name
        dest = new_root / spec / "hinted" / src.name
        if dest.exists():
            continue
        moves.append((src.as_posix(), dest.as_posix()))
        if not apply:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        meta_path = dest / "run_meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        meta.update({"label": "hinted", "migrated_from": src.as_posix()})
        meta_path.write_text(json.dumps(meta, indent=1), encoding="utf-8")
        log = old_root / f"{spec}-full-seed{m.group(1)}.log"
        log_dest = new_root / f"{spec}-hinted-seed{m.group(1)}.log"
        if log.exists() and not log_dest.exists():
            shutil.move(str(log), str(log_dest))
    return moves


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--old", default="runs/bench")
    ap.add_argument("--new", default="runs/bench2")
    ap.add_argument("--apply", action="store_true", help="move (without it, only list)")
    a = ap.parse_args(argv)
    moves = migrate(Path(a.old), Path(a.new), a.apply)
    for src, dest in moves:
        print(f"{'moved' if a.apply else 'would move'} {src} -> {dest}")
    print(f"{len(moves)} finished hinted-prompt runs {'moved' if a.apply else 'to move (add --apply)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
