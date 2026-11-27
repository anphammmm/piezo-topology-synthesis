import unittest
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SourceHygieneTest(unittest.TestCase):
    def test_no_syntax_warnings(self):
        """Invalid escape sequences (a backslash before %) warn on Panda's Python 3.12 every time the module loads."""
        for f in sorted(list((ROOT / "piezo_synth").glob("*.py")) + list((ROOT / "tools").glob("*.py"))):
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                try:
                    compile(f.read_text(encoding="utf-8"), str(f), "exec")
                except SyntaxError as e:
                    self.fail(f"{f.name}: {e}")


if __name__ == "__main__":
    unittest.main()
