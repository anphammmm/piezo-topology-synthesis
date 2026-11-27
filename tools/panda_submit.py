"""Submit a command as a Panda job from the notebook's terminal (for Claude Code, or a person).

    python3 tools/panda_submit.py --name piezo-smoke -- \
        "rm -rf runs/smoke && python3 -u -m piezo_synth.run --smoke --out runs/smoke"

The job runs in this repository's folder on /work (same files), on the ltspice-cpu image, without a
GPU. Its output is also written to runs/logs/<name>.log, because the cluster deletes job logs 48 hours
after a job ends. Every submission is appended to runs/jobs.jsonl. --follow waits and prints the log
(like log() in the notebook); without it the command returns at once with the job name.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

NAMESPACE_FILE = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"


def ltspice_image() -> str:
    ns = Path(NAMESPACE_FILE).read_text().strip()
    return f"image-registry.openshift-image-registry.svc:5000/{ns}/ltspice-cpu:latest"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True, help="job name prefix, e.g. piezo-smoke")
    ap.add_argument("--cpus", type=int, default=8)
    ap.add_argument("--memory", default="16Gi")
    ap.add_argument("--timeout", type=int, default=4 * 3600, help="seconds, counted from when the job starts")
    ap.add_argument("--follow", action="store_true", help="wait for the job and print its output")
    ap.add_argument("--image", help="default: this namespace's ltspice-cpu image")
    ap.add_argument("--work-root", default="/work", help=argparse.SUPPRESS)
    ap.add_argument("--cwd", default=None, help=argparse.SUPPRESS)
    ap.add_argument("command", nargs=argparse.REMAINDER, help="after --: the shell command to run")
    a = ap.parse_args(argv)
    cmd = " ".join(a.command[1:] if a.command[:1] == ["--"] else a.command).strip()
    if not cmd:
        ap.error("no command given (put it after --)")
    if "'" in cmd:
        ap.error("the command may not contain single quotes (it is wrapped in bash -c '...'); use double quotes")
    cwd = Path(a.cwd or os.getcwd()).resolve()
    try:
        subdir = cwd.relative_to(Path(a.work_root).resolve()).as_posix()
    except ValueError:
        ap.error(f"run this from a folder under {a.work_root} (jobs only see {a.work_root}); now in {cwd}")
    logs = cwd / "runs" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    logfile = f"runs/logs/{a.name}.log"
    wrapped = f"bash -o pipefail -c '{cmd} 2>&1 | tee {logfile}'"
    from gpu import run, log   # the platform's job API, available in the notebook and its terminal
    job = run(wrapped, image=a.image or ltspice_image(), gpus=0, cpus=a.cpus, memory=a.memory,
              timeout=a.timeout, name=a.name, subdir=subdir)
    with (cwd / "runs" / "jobs.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "job": job, "name": a.name,
                            "command": cmd, "log": logfile}) + "\n")
    print(f"submitted {job}: output also in {logfile}", flush=True)
    if a.follow:
        log(job)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
