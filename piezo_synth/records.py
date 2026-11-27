"""Incremental run record: events, candidates, measurements, checks, progress, timing, model exchanges.

Every write is an append or an atomic replace, so a job that is killed leaves a usable record.
"""
from __future__ import annotations

import csv
import json
import os
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from .circuit import Circuit, to_dict
from .evaluate import Evaluation
from .netlist import MEAS_NAMES

CANDIDATE_FIELDS = ["id", "iteration", "origin", "parent", "move", "name", "topo_hash", "design_hash",
                    "n_components", "split", "scalar", "cond_pass", "checks_pass", "all_pass"]
MEAS_FIELDS = ["candidate", "split", "condition", *MEAS_NAMES, "dv", "sim_ok", "sim_error"]
PROPOSAL_FIELDS = ["round", "k", "name", "move", "topo_hash", "status", "candidate", "of", "worst_ratio",
                   *[f"ratio_{c}" for c in ("S2", "S4", "S6")], *[f"gain_{c}" for c in ("S2", "S4", "S6")],
                   "n_presets", "hints", "problems"]
CHECK_FIELDS = ["candidate", "split", "condition", "criterion", "measured", "op", "limit", "margin", "passed"]


@dataclass
class Candidate:
    id: str
    iteration: int
    origin: str            # reference | witness | llm | size | refine | audit
    parent: Optional[str]
    circuit: Circuit
    topo_hash: str
    design_hash: str
    evaluation: Evaluation
    move: str
    name: str
    n_components: int


class RunRecorder:
    def __init__(self, out_dir: Path, quiet: bool = False):
        self.out = Path(out_dir)
        self.out.mkdir(parents=True, exist_ok=True)
        self.quiet = quiet
        self.t0 = time.time()
        self._lock = threading.Lock()
        self._progress: dict = {}

    def elapsed(self) -> float:
        return time.time() - self.t0

    # -------------------------------------------------------------- console
    def log(self, phase: str, msg: str) -> None:
        if self.quiet:
            return
        e = int(self.elapsed())
        print(f"[{e // 3600:02d}:{e % 3600 // 60:02d}:{e % 60:02d}] [{phase:<7}] {msg}", flush=True)

    # -------------------------------------------------------------- files
    def write_json(self, name: str, obj) -> None:
        path = self.out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")
        os.replace(tmp, path)

    def _append_csv(self, name: str, fields, rows) -> None:
        path = self.out / name
        new = not path.exists()
        with path.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            if new:
                w.writeheader()
            for r in rows:
                w.writerow(r)

    def event(self, kind: str, **data) -> None:
        with self._lock:
            with (self.out / "events.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps({"t": round(self.elapsed(), 2), "kind": kind, **data}, default=str) + "\n")

    def candidate(self, c: Candidate, split: str = "search") -> None:
        ev = c.evaluation
        with self._lock:
            self._append_csv("candidates.csv", CANDIDATE_FIELDS, [{
                "id": c.id, "iteration": c.iteration, "origin": c.origin, "parent": c.parent or "",
                "move": c.move, "name": c.name, "topo_hash": c.topo_hash, "design_hash": c.design_hash,
                "n_components": c.n_components, "split": split, "scalar": round(ev.scalar, 4),
                "cond_pass": ev.cond_pass, "checks_pass": ev.checks_pass, "all_pass": ev.all_pass}])
            rows = []
            for cond, m in ev.meas.items():
                r = {"candidate": c.id, "split": split, "condition": cond, "sim_ok": ev.sim_ok.get(cond),
                     "sim_error": " ".join(ev.sim_error.get(cond, "").split())[:300]}
                r.update({k: m.get(k) for k in (*MEAS_NAMES, "dv")})
                rows.append(r)
            self._append_csv("measurements.csv", MEAS_FIELDS, rows)
            self._append_csv("checks.csv", CHECK_FIELDS, [
                {"candidate": c.id, "split": split, **{k: v for k, v in asdict(ch).items()}} for ch in ev.checks])
        folder = self.out / "candidates" / c.id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "circuit.json").write_text(json.dumps(to_dict(c.circuit), indent=1), encoding="utf-8")

    def proposal(self, row: dict) -> None:
        """One row per design the model proposed: its fate (invalid, duplicate, screen_failed, evaluated)."""
        with self._lock:
            self._append_csv("proposals.csv", PROPOSAL_FIELDS, [row])

    def progress(self, **fields) -> None:
        with self._lock:
            self._progress.update(fields)
            self._progress["elapsed_s"] = round(self.elapsed(), 1)
            snapshot = dict(self._progress)
        self.write_json("progress.json", snapshot)

    def llm_exchange(self, iteration: int, attempt: int, messages, reply) -> None:
        self.write_json(f"llm/iter-{iteration:02d}-{attempt}.json",
                        {"iteration": iteration, "attempt": attempt, "messages": messages, "reply": asdict(reply)})

    def timing(self, d: dict) -> None:
        self.write_json("timing.json", d)
