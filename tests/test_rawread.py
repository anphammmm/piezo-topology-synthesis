import struct
import tempfile
import unittest
from pathlib import Path

from piezo_synth.rawread import read_raw

HEADER = ("Title: * test\nDate: today\nPlotname: Transient Analysis\nFlags: real forward\n"
          "No. Variables: 2\nNo. Points: 3\nOffset: 0.0\nCommand: LTspice\nVariables:\n"
          "\t0\ttime\ttime\n\t1\tV(out)\tvoltage\n")


class RawTest(unittest.TestCase):
    def test_read_raw_binary_utf16(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.raw"
            data = b"".join(struct.pack("<df", t, v) for t, v in [(0.0, 0.5), (-1e-3, 1.5), (2e-3, 2.5)])
            p.write_bytes((HEADER + "Binary:\n").encode("utf-16-le") + data)
            r = read_raw(p)
            self.assertAlmostEqual(r["time"][1], 1e-3)        # sign flag removed
            self.assertAlmostEqual(r["time"][2], 2e-3)
            self.assertAlmostEqual(r["V(out)"][1], 1.5)

    def test_read_raw_binary_double(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "b.raw"
            hdr = HEADER.replace("real forward", "real forward double")
            data = b"".join(struct.pack("<dd", t, v) for t, v in [(0.0, 0.5), (1e-3, 1.25), (2e-3, 2.5)])
            p.write_bytes((hdr + "Binary:\n").encode("latin-1") + data)
            self.assertAlmostEqual(read_raw(p)["V(out)"][1], 1.25)

    def test_read_raw_ascii(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.raw"
            vals = "Values:\n0\t0.0\n\t0.5\n1\t0.001\n\t1.5\n2\t0.002\n\t2.5\n"
            p.write_text(HEADER + vals, encoding="latin-1")
            r = read_raw(p)
            self.assertEqual(r["V(out)"], [0.5, 1.5, 2.5])


if __name__ == "__main__":
    unittest.main()
