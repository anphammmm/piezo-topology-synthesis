import tempfile
import time
import unittest
from pathlib import Path

from piezo_synth.sim import SimResult, Simulator
from tests.fakes import FakeBackend


def index_of(text):
    return {"vavg": float(text.split()[-1])}


class SimTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_parallel_results_in_order(self):
        def slow(t):
            time.sleep(0.05)
            return index_of(t)
        s = Simulator(FakeBackend(slow), self.root, workers=4)
        t = time.time()
        res = s.run([(f"j{i}", f"netlist {i}") for i in range(6)])
        self.assertEqual([r.meas["vavg"] for r in res], [0, 1, 2, 3, 4, 5])
        self.assertTrue(all(isinstance(r, SimResult) and r.ok for r in res))
        self.assertLess(time.time() - t, 0.25)    # ran in parallel
        self.assertEqual(s.stats["n_sims"], 6)

    def test_cache_hit_no_backend_call(self):
        be = FakeBackend(lambda t: {"vavg": 2.0})
        s = Simulator(be, self.root, workers=2)
        s.run([("a", "X 1")])
        r = s.run([("b", "X 1")])
        self.assertEqual(len(be.calls), 1)
        self.assertTrue(r[0].cached)
        self.assertEqual(r[0].meas, {"vavg": 2.0})
        self.assertEqual(s.stats["cache_hits"], 1)

    def test_duplicates_within_one_call_simulated_once(self):
        be = FakeBackend(lambda t: {"vavg": 1.0})
        res = Simulator(be, self.root).run([("a", "Y 1"), ("b", "Y 1")])
        self.assertEqual(len(be.calls), 1)
        self.assertEqual(len(res), 2)

    def test_cache_persists_across_instances(self):
        be = FakeBackend(lambda t: {"vavg": 3.0})
        Simulator(be, self.root).run([("a", "Z 1")])
        be2 = FakeBackend(lambda t: {"vavg": 9.0})
        r = Simulator(be2, self.root).run([("a", "Z 1")])[0]
        self.assertEqual(be2.calls, [])
        self.assertEqual(r.meas["vavg"], 3.0)

    def test_failures_not_persisted_across_instances(self):
        Simulator(FakeBackend(lambda t: None), self.root).run([("a", "F 1")])
        be2 = FakeBackend(lambda t: {"vavg": 2.0})
        r = Simulator(be2, self.root).run([("a", "F 1")])[0]
        self.assertEqual(len(be2.calls), 1)
        self.assertTrue(r.ok)

    def test_failures_cached_within_instance(self):
        be = FakeBackend(lambda t: None)
        s = Simulator(be, self.root)
        s.run([("a", "F 2")]); s.run([("a", "F 2")])
        self.assertEqual(len(be.calls), 1)

    def test_backend_exception_becomes_failed_result(self):
        r = Simulator(FakeBackend(lambda t: 1 / 0), self.root).run([("a", "X 1")])[0]
        self.assertFalse(r.ok)
        self.assertIn("ZeroDivisionError", r.error)

    def test_failed_sim_reported(self):
        r = Simulator(FakeBackend(lambda t: None), self.root).run([("a", "X 1")])[0]
        self.assertFalse(r.ok)
        self.assertIn("singular", r.error)


if __name__ == "__main__":
    unittest.main()


def writes_raw(text, folder, timeout):
    """Backend that, like LTspice, leaves a waveform file (and an operating-point one) in the folder."""
    Path(folder).mkdir(parents=True, exist_ok=True)
    (Path(folder) / "circuit.net").write_text(text)
    (Path(folder) / "circuit.log").write_text("vavg: 2.5")
    (Path(folder) / "circuit.raw").write_bytes(b"\0" * 4096)
    (Path(folder) / "circuit.op.raw").write_bytes(b"\0" * 64)

    class R:
        ok, meas, error = True, {"vavg": 2.5}, ""
    return R()


class RawCleanupTest(unittest.TestCase):
    def test_raw_files_deleted_after_measurements_are_read(self):
        with tempfile.TemporaryDirectory() as d:
            res = Simulator(writes_raw, Path(d)).run([("a", "net a")])[0]
            self.assertTrue(res.ok)
            self.assertEqual(res.meas, {"vavg": 2.5})
            folder = Path(res.folder)
            self.assertEqual(list(folder.glob("*.raw")), [])
            self.assertTrue((folder / "circuit.log").exists())
            self.assertTrue((folder / "circuit.net").exists())

    def test_keep_raw_for_waveforms(self):
        with tempfile.TemporaryDirectory() as d:
            res = Simulator(writes_raw, Path(d), keep_raw=True).run([("a", "net a")])[0]
            self.assertTrue((Path(res.folder) / "circuit.raw").exists())
