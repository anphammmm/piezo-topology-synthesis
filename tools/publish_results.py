"""Publish the light part of the run folders to the `results` branch on GitHub, so the results can be
read (and the code fixed) from another machine. Runs from Panda's notebook; needs git and network
access to github.com (GIT_ASKPASS supplies the token, see tools/git_askpass.sh).

    python3 tools/publish_results.py --message "smoke test after the diode fix"

Published: reports, JSON, CSV, logs, netlists and LTspice logs (each at most a few MB), plus a listing
of every simulation folder (sims_index.txt). Never published: .raw waveforms and anything larger.
The results branch is kept in a separate worktree beside the repository (<repo>-results), so the
repository's own checkout and branch are not touched.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import time
from collections import defaultdict
from pathlib import Path

BRANCH = "results"
KEEP_SUFFIXES = {".md", ".json", ".jsonl", ".csv", ".log", ".txt", ".net", ".tex", ".png", ".pdf"}
MAX_FILE = 5 * 2**20            # bytes, outside sims/
MAX_SIM_FILE = 200 * 2**10      # bytes, inside sims/ (netlists and LTspice logs only)
MAX_SIM_FILES = 60              # per run folder


def git(cwd, *args, check=True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=check,
                          env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})


def _ensure_worktree(repo: Path, wt: Path) -> None:
    git(repo, "fetch", "--quiet", "origin", check=False)
    remote_has = bool(git(repo, "ls-remote", "--heads", "origin", BRANCH, check=False).stdout.strip())
    if wt.exists():
        if remote_has:
            git(wt, "pull", "--quiet", "--ff-only", "origin", BRANCH, check=False)
        return
    git(repo, "worktree", "prune", check=False)
    if remote_has:
        git(repo, "worktree", "add", "--quiet", "-B", BRANCH, str(wt), f"origin/{BRANCH}")
    else:
        git(repo, "worktree", "add", "--quiet", "--detach", str(wt))
        git(wt, "checkout", "--quiet", "--orphan", BRANCH)
        git(wt, "rm", "-r", "-f", "--quiet", ".", check=False)
        for p in wt.iterdir():          # files git did not track (none expected) are removed too
            if p.name != ".git":
                shutil.rmtree(p) if p.is_dir() else p.unlink()


def _collect(repo: Path):
    """[(source, relative destination)] and {run folder: sims listing lines}."""
    picked, sim_counts = [], defaultdict(int)
    listings = defaultdict(list)
    runs = repo / "runs"
    for f in sorted(runs.rglob("*")) if runs.exists() else []:
        if not f.is_file():
            continue
        rel = f.relative_to(repo)
        parts = rel.parts
        size = f.stat().st_size
        if "sims" in parts:
            k = parts.index("sims")
            run_dir = Path(*parts[:k])
            listings[run_dir].append(f"{Path(*parts[k + 1:]).as_posix()}\t{size}")
            if f.suffix in (".log", ".net") and size <= MAX_SIM_FILE and sim_counts[run_dir] < MAX_SIM_FILES:
                sim_counts[run_dir] += 1
                picked.append((f, rel))
            continue
        if f.suffix.lower() in KEEP_SUFFIXES and size <= MAX_FILE:
            picked.append((f, rel))
    gen = repo / "paper" / "generated"
    for f in sorted(gen.rglob("*")) if gen.exists() else []:
        if f.is_file() and f.stat().st_size <= MAX_FILE:
            picked.append((f, Path("paper_generated") / f.relative_to(gen)))
    return picked, listings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--message", default="", help="what these results are (goes in the commit message)")
    a = ap.parse_args(argv)
    repo = Path(a.repo).resolve()
    wt = repo.parent / f"{repo.name}-results"
    _ensure_worktree(repo, wt)
    picked, listings = _collect(repo)
    for src, rel in picked:
        dst = wt / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    for run_dir, lines in listings.items():
        out = wt / run_dir / "sims_index.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("file\tbytes\n" + "\n".join(lines[:5000]) + "\n", encoding="utf-8")
    git(wt, "add", "-A")
    if git(wt, "diff", "--cached", "--quiet", check=False).returncode == 0:
        print("nothing new to publish")
        return 0
    head = git(repo, "rev-parse", "--short", "HEAD", check=False).stdout.strip()
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    (wt / "PUBLISHED.md").write_text(
        f"# Results published from Panda\n\nLast publish: {stamp}, code at commit {head}.\n\n"
        f"{a.message}\n", encoding="utf-8")
    git(wt, "add", "-A")
    name = git(repo, "config", "user.name", check=False).stdout.strip() or "Panda results"
    email = git(repo, "config", "user.email", check=False).stdout.strip() or "panda-results@noreply.invalid"
    msg = f"results {stamp} (code {head})" + (f": {a.message}" if a.message else "")
    git(wt, "-c", f"user.name={name}", "-c", f"user.email={email}", "commit", "--quiet", "-m", msg)
    p = git(wt, "push", "--quiet", "-u", "origin", BRANCH, check=False)
    if p.returncode != 0:
        print("push failed:", p.stderr.strip()[-500:])
        return 1
    n = len(picked) + len(listings)
    print(f"published {n} files to branch '{BRANCH}': {msg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
