import subprocess
import tempfile
import unittest
from pathlib import Path

from tools import publish_results


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True).stdout


class PublishTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.remote = root / "remote.git"
        subprocess.run(["git", "init", "-q", "--bare", str(self.remote)], check=True)
        self.repo = root / "work" / "me" / "repo"
        self.repo.mkdir(parents=True)
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        (self.repo / "README.md").write_text("x")
        (self.repo / ".gitignore").write_text("runs/\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "init")
        git(self.repo, "remote", "add", "origin", str(self.remote))
        git(self.repo, "push", "-q", "origin", "main")
        run = self.repo / "runs" / "smoke"
        (run / "sims" / "abc123").mkdir(parents=True)
        (run / "report.md").write_text("# report")
        (run / "measurements.csv").write_text("a,b\n1,2\n")
        (run / "sims" / "abc123" / "circuit.net").write_text("* net")
        (run / "sims" / "abc123" / "circuit.log").write_text("LTspice log")
        (run / "sims" / "abc123" / "circuit.raw").write_bytes(b"\0" * 1000)
        (run / "huge.json").write_bytes(b"{" + b" " * (6 * 2**20) + b"}")
        (self.repo / "runs" / "logs").mkdir()
        (self.repo / "runs" / "logs" / "piezo-smoke.log").write_text("[done] ok")

    def tearDown(self):
        self.tmp.cleanup()

    def published(self):
        return set(git(self.remote, "ls-tree", "-r", "--name-only", "results").split())

    def test_publishes_light_results_to_results_branch(self):
        rc = publish_results.main(["--repo", str(self.repo), "--message", "smoke done"])
        self.assertEqual(rc, 0)
        files = self.published()
        for f in ("runs/smoke/report.md", "runs/smoke/measurements.csv", "runs/smoke/sims_index.txt",
                  "runs/smoke/sims/abc123/circuit.log", "runs/smoke/sims/abc123/circuit.net",
                  "runs/logs/piezo-smoke.log", "PUBLISHED.md"):
            self.assertIn(f, files)
        self.assertNotIn("runs/smoke/sims/abc123/circuit.raw", files)
        self.assertNotIn("runs/smoke/huge.json", files)
        index = git(self.remote, "show", "results:runs/smoke/sims_index.txt")
        self.assertIn("circuit.raw", index)          # listed (with its size) but not copied
        self.assertIn("smoke done", git(self.remote, "log", "-1", "--format=%s", "results"))
        self.assertEqual(git(self.repo, "rev-parse", "--abbrev-ref", "HEAD").strip(), "main")

    def test_second_publish_adds_new_files_and_skips_empty_commit(self):
        publish_results.main(["--repo", str(self.repo)])
        n1 = int(git(self.remote, "rev-list", "--count", "results"))
        publish_results.main(["--repo", str(self.repo)])
        self.assertEqual(int(git(self.remote, "rev-list", "--count", "results")), n1)
        (self.repo / "runs" / "smoke" / "summary.json").write_text("{}")
        publish_results.main(["--repo", str(self.repo)])
        self.assertIn("runs/smoke/summary.json", self.published())
        self.assertEqual(int(git(self.remote, "rev-list", "--count", "results")), n1 + 1)


if __name__ == "__main__":
    unittest.main()
