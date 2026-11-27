"""Test doubles for LTspice and Gemma."""
import threading


class _Res:
    def __init__(self, ok, meas, error, folder):
        self.ok, self.meas, self.error, self.folder = ok, meas, error, folder


class FakeBackend:
    """Stands in for ltspice_run.simulate. fn(netlist_text) -> dict of measurements, or None for a
    failed simulation. Records every call."""

    def __init__(self, fn):
        self.fn = fn
        self.calls = []
        self._lock = threading.Lock()

    def __call__(self, text, folder, timeout):
        with self._lock:
            self.calls.append(text)
        meas = self.fn(text)
        if meas is None:
            return _Res(False, {}, "singular matrix: fake failure", folder)
        return _Res(True, dict(meas), "", folder)
