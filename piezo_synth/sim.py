"""Run LTspice netlists in parallel threads, with a persistent content-hash cache and timing."""
from __future__ import annotations

import hashlib
import json
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple


@dataclass
class SimResult:
    ok: bool
    meas: dict
    error: str
    seconds: float
    folder: str
    cached: bool = False


def ltspice_backend() -> Callable[[str, str, float], Any]:
    """The project's LTspice helper (in the ltspice-cpu image), imported on first use."""
    import sys
    if "/opt/ltspice" not in sys.path:
        sys.path.append("/opt/ltspice")
    from ltspice_run import simulate  # type: ignore

    def backend(text: str, folder: str, timeout: float):
        return simulate(text, folder, timeout=timeout)
    return backend


class Simulator:
    """backend(netlist_text, folder, timeout) -> object with .ok, .meas, .error (ltspice_run.simulate)."""

    def __init__(self, backend: Callable[[str, str, float], Any], root: Path, workers: int = 8,
                 timeout: float = 120.0, keep_raw: bool = False):
        self.backend = backend
        self.keep_raw = keep_raw     # waveform files are deleted once the measurements are read
        self.root = Path(root)
        self.workers = max(1, int(workers))
        self.timeout = timeout
        self.root.mkdir(parents=True, exist_ok=True)
        self._cache_file = self.root / "sim_cache.jsonl"
        self._cache: Dict[str, SimResult] = {}
        self._lock = threading.Lock()
        self.stats = {"n_sims": 0, "cache_hits": 0, "sim_seconds": 0.0, "wall_seconds": 0.0, "failures": 0}
        if self._cache_file.exists():
            for line in self._cache_file.read_text(encoding="utf-8").splitlines():
                try:
                    d = json.loads(line)
                    self._cache[d["key"]] = SimResult(**d["result"])
                except (ValueError, KeyError, TypeError):
                    continue

    @staticmethod
    def key(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def _one(self, key: str, text: str) -> SimResult:
        folder = self.root / "sims" / key[:16]
        t = time.time()
        try:
            r = self.backend(text, str(folder), self.timeout)
            res = SimResult(bool(getattr(r, "ok", False)), dict(getattr(r, "meas", {}) or {}),
                            str(getattr(r, "error", "") or ""), round(time.time() - t, 3), str(folder))
            cacheable = True
        except Exception as e:   # a crashed backend must not stop the search
            res = SimResult(False, {}, f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=2)}",
                            round(time.time() - t, 3), str(folder))
            cacheable = False
        if not self.keep_raw:
            self._drop_raw(folder)
        with self._lock:
            self.stats["n_sims"] += 1
            self.stats["sim_seconds"] += res.seconds
            self.stats["failures"] += 0 if res.ok else 1
            if cacheable:
                self._cache[key] = res
            if cacheable and res.ok:   # failures (timeouts, Wine trouble) are retried by a later run here
                with self._cache_file.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({"key": key, "result": asdict(res)}) + "\n")
        return res

    @staticmethod
    def _drop_raw(folder: Path) -> None:
        """The .raw waveforms are the bulk of a simulation folder (MB each, tens of thousands per
        campaign) and are not needed once the .meas results are in hand; netlist and log stay."""
        if not folder.exists():
            return
        for f in folder.rglob("*.raw"):
            try:
                f.unlink()
            except OSError:
                pass

    def run(self, jobs: List[Tuple[str, str]]) -> List[SimResult]:
        """jobs: (label, netlist_text). Results come back in input order."""
        t = time.time()
        keys = [self.key(text) for _, text in jobs]
        todo: Dict[str, str] = {}
        with self._lock:
            for k, (_, text) in zip(keys, jobs):
                if k not in self._cache and k not in todo:
                    todo[k] = text
        fresh: Dict[str, SimResult] = {}
        if todo:
            with ThreadPoolExecutor(max_workers=min(self.workers, len(todo))) as ex:
                futs = {k: ex.submit(self._one, k, text) for k, text in todo.items()}
                for k, f in futs.items():
                    fresh[k] = f.result()
        out = []
        returned = set()
        with self._lock:
            for k in keys:
                if k in fresh and k not in returned:
                    returned.add(k)
                    out.append(fresh[k])
                else:
                    base = fresh.get(k) or self._cache[k]
                    if k not in fresh:
                        self.stats["cache_hits"] += 1
                    out.append(SimResult(base.ok, dict(base.meas), base.error, base.seconds, base.folder,
                                         cached=True))
            self.stats["wall_seconds"] += time.time() - t
        return out
