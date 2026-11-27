import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

from tools import panda_submit


class FakeGpu(types.ModuleType):
    def __init__(self):
        super().__init__("gpu")
        self.calls, self.logged = [], []

    def run(self, cmd, **kw):
        self.calls.append((cmd, kw))
        return "piezo-smoke-abc12"

    def log(self, name):
        self.logged.append(name)


class PandaSubmitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name) / "work"
        self.repo = self.work / "hpham" / "piezo-topology-synthesis"
        self.repo.mkdir(parents=True)
        self.gpu = FakeGpu()
        sys.modules["gpu"] = self.gpu

    def tearDown(self):
        sys.modules.pop("gpu", None)
        self.tmp.cleanup()

    def submit(self, *args):
        return panda_submit.main(["--work-root", str(self.work), "--cwd", str(self.repo),
                                  "--image", "registry/ns/ltspice-cpu:latest", *args])

    def test_submits_cpu_job_in_repo_folder_with_tee(self):
        rc = self.submit("--name", "piezo-smoke", "--", "python3 -u -m piezo_synth.run --smoke --out runs/smoke")
        self.assertEqual(rc, 0)
        cmd, kw = self.gpu.calls[0]
        self.assertEqual(kw["gpus"], 0)
        self.assertEqual(kw["subdir"], "hpham/piezo-topology-synthesis")
        self.assertEqual(kw["image"], "registry/ns/ltspice-cpu:latest")
        self.assertEqual((kw["cpus"], kw["memory"], kw["name"]), (8, "16Gi", "piezo-smoke"))
        self.assertTrue(cmd.startswith("bash -o pipefail -c '"))
        self.assertIn("2>&1 | tee runs/logs/piezo-smoke.log", cmd)
        self.assertEqual(self.gpu.logged, [])
        rec = json.loads((self.repo / "runs" / "jobs.jsonl").read_text().splitlines()[-1])
        self.assertEqual(rec["job"], "piezo-smoke-abc12")
        self.assertTrue((self.repo / "runs" / "logs").is_dir())

    def test_follow_calls_log(self):
        self.submit("--name", "x", "--follow", "--", "echo hi")
        self.assertEqual(self.gpu.logged, ["piezo-smoke-abc12"])

    def test_refuses_single_quotes_and_paths_outside_work(self):
        with self.assertRaises(SystemExit):
            self.submit("--name", "x", "--", "echo 'quoted'")
        with self.assertRaises(SystemExit):
            panda_submit.main(["--work-root", str(self.work), "--cwd", self.tmp.name, "--image", "i",
                               "--name", "x", "--", "echo hi"])
        self.assertEqual(self.gpu.calls, [])


if __name__ == "__main__":
    unittest.main()


class PandaCampaignTest(PandaSubmitTest):
    def test_campaign_submits_one_job_per_chosen_variant(self):
        from tools import panda_campaign
        rc = panda_campaign.main(["--work-root", str(self.work), "--cwd", str(self.repo), "--image", "img",
                                  "--seeds", "1,2", "--variants", "full,random"])
        self.assertEqual(rc, 0)
        names = [kw["name"] for _, kw in self.gpu.calls]
        self.assertEqual(names, ["piezo-full", "piezo-random"])
        self.assertIn("--baseline random", self.gpu.calls[1][0])
        self.assertTrue((self.repo / "runs" / "exp" / "full.json").exists())
        self.assertEqual(self.gpu.calls[0][1]["timeout"], 12 * 3600)

    def test_bench_submits_one_job_per_spec(self):
        from tools import panda_campaign
        rc = panda_campaign.main(["--work-root", str(self.work), "--cwd", str(self.repo), "--image", "img",
                                  "--bench", "--specs", "P2,P3", "--seeds", "1"])
        self.assertEqual(rc, 0)
        self.assertEqual([kw["name"] for _, kw in self.gpu.calls], ["piezo-bench-p2", "piezo-bench-p3"])
        cmd = self.gpu.calls[0][0]
        for v in ("full", "no_screen", "no_diag", "coord", "random"):
            self.assertIn(f"runs/bench/P2/{v}/seed1", cmd)
        self.assertNotIn("--spec P3", cmd)
        self.assertTrue((self.repo / "runs" / "bench" / "random.json").exists())
