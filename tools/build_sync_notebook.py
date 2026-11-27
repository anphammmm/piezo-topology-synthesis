"""Generate panda_sync.ipynb: run the repository's code on Panda and publish the results to GitHub.

    python tools/build_sync_notebook.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INTRO = """# Panda <-> GitHub: chạy code mới nhất, đẩy kết quả lên GitHub

Notebook này chỉ có 4 ô. Code nằm trên GitHub (`anphammmm/piezo-topology-synthesis`). Ô 1 lấy bản mới
nhất về, ô 2 chạy việc trên Panda (job LTspice, không dùng GPU), ô 3 xem tiến độ, ô 4 đẩy kết quả gọn
(báo cáo, CSV, log, không có waveform) lên nhánh `results`. Claude trên laptop đọc kết quả từ
nhánh đó, sửa code, push. Bạn chạy lại ô 1 là có bản sửa.

**Đặt notebook này ở ngoài thư mục repo**, ví dụ `/work/hpham/panda_sync.ipynb`. Jupyter lưu output vào
file notebook; nếu nó nằm trong repo thì `git pull` sẽ bị chặn vì file đã bị sửa.

Lần đầu: tạo file token theo `docs/panda-sync.md` (bước 1-2), rồi chạy ô 1.
"""

SETUP = '''import os, sys, json, glob, time, subprocess, importlib
from pathlib import Path

ME = "hpham"                                    # <-- tên thư mục của bạn trong /work
GITHUB_USER = "anphammmm"
URL = "https://github.com/anphammmm/piezo-topology-synthesis.git"
BRANCH = "feat/v2-screen-size-paper"
REPO = Path(f"/work/{ME}/piezo-topology-synthesis")
SECRETS = Path(f"/work/{ME}/.secrets")
TOKEN_FILE = SECRETS / "github_token"

assert TOKEN_FILE.exists(), f"chưa có token: tạo {TOKEN_FILE} theo docs/panda-sync.md (bước 2)"
ASKPASS = SECRETS / "askpass.sh"                # git gets the token from here; it is never printed
ASKPASS.write_text('#!/bin/sh\\ncase "$1" in Username*) echo "$GITHUB_USER" ;; *) cat "$PIEZO_TOKEN_FILE" ;; esac\\n')
ASKPASS.chmod(0o700)
ENV = dict(os.environ, GIT_ASKPASS=str(ASKPASS), GIT_TERMINAL_PROMPT="0", GITHUB_USER=GITHUB_USER,
           PIEZO_TOKEN_FILE=str(TOKEN_FILE))

def sh(*cmd, cwd=REPO, check=True):
    p = subprocess.run(cmd, cwd=cwd, env=ENV, capture_output=True, text=True)
    out = (p.stdout + p.stderr).strip()
    if out:
        print(out[-3000:])
    if check and p.returncode != 0:
        raise RuntimeError(f"failed: {' '.join(cmd)}")
    return p

if not REPO.exists():
    sh("git", "clone", "--quiet", URL, str(REPO), cwd=REPO.parent)
sh("git", "config", "user.name", f"{GITHUB_USER} (Panda)")
sh("git", "config", "user.email", f"{GITHUB_USER}@users.noreply.github.com")
sh("git", "fetch", "--quiet", "origin")
sh("git", "checkout", "--quiet", BRANCH)
sh("git", "pull", "--ff-only", "--quiet", "origin", BRANCH)
sh("git", "log", "-1", "--format=code: %h %s (%cr)")

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))               # the repository has no gpu.py, so nothing is shadowed
import piezo_synth.experiments, tools.panda_submit, tools.panda_campaign
for m in (piezo_synth.experiments, tools.panda_submit, tools.panda_campaign):
    importlib.reload(m)                          # pick up code just pulled
from gpu import jobs, log, cancel

def submit(name, cmd, timeout=4 * 3600):
    tools.panda_submit.main(["--cwd", str(REPO), "--name", name, "--timeout", str(timeout), "--", cmd])
print("ready")'''

TASK_MD = """## 2. Chạy việc

Đặt `TASK` rồi chạy ô. Mỗi lần chỉ nên chạy một việc có LTspice (chúng dùng chung Wine).
- `"smoke"`: kiểm tra nhanh, khoảng 2 phút (chạy đầu tiên, và sau mỗi lần đổi mô hình linh kiện).
- `"single"`: một lần tìm kiếm đầy đủ, khoảng 30-60 phút.
- `"waves"`: waveform của thiết kế tốt nhất trong lần `single` gần nhất.
- `"campaign"`: toàn bộ thí nghiệm cho paper (8 biến thể x 5 seed, vài tiếng; chạy lại thì chạy tiếp)."""

TASK = '''TASK = "smoke"
stamp = time.strftime("%Y%m%d-%H%M%S")
if TASK == "smoke":
    submit("piezo-smoke", "rm -rf runs/smoke && python3 -u -m piezo_synth.run --smoke --out runs/smoke", 3600)
elif TASK == "single":
    submit("piezo-single", f"python3 -u -m piezo_synth.run --out runs/single-{stamp}")
elif TASK == "waves":
    sel = sorted(REPO.glob("runs/single-*/selected/circuit.json"))
    assert sel, "chưa có lần chạy single nào hoàn tất"
    run_dir = sel[-1].parent.parent.relative_to(REPO).as_posix()
    submit("piezo-waves",
           f"python3 -u -m piezo_synth.reproduce {run_dir}/selected/circuit.json --out {run_dir}/waves-selected "
           f"--conditions S1,S4 --waveforms && python3 -u -m piezo_synth.reproduce "
           f"{run_dir}/candidates/c0000/circuit.json --out {run_dir}/waves-reference --conditions S1,S4 --waveforms",
           1800)
elif TASK == "campaign":
    tools.panda_campaign.main(["--cwd", str(REPO)])
else:
    raise ValueError(TASK)'''

STATUS_MD = """## 3. Tiến độ (chạy bất cứ lúc nào)"""

STATUS = '''jobs()
for f in sorted(REPO.glob("runs/logs/*.log"), key=lambda p: p.stat().st_mtime)[-2:]:
    print(f"\\n===== {f.relative_to(REPO)} (last lines) =====")
    print("\\n".join(f.read_text(errors="replace").splitlines()[-15:]))
done = len(glob.glob(str(REPO / "runs/exp/*/seed*/outcome.json")))
if (REPO / "runs/exp").exists():
    print(f"\\ncampaign: {done} of 40 runs finished")'''

PUBLISH_MD = """## 4. Đẩy kết quả lên GitHub

Chạy khi một việc đã xong (hoặc giữa chừng: kết quả dở dang cũng đẩy được). Nếu đã có campaign, ô này
tổng hợp các bảng cho paper trước. Viết vài chữ vào `MESSAGE` để Claude biết đây là kết quả gì."""

PUBLISH = '''MESSAGE = "smoke test"
if (REPO / "runs/exp").exists():
    sh(sys.executable, "-m", "piezo_synth.experiments", "runs/exp", "--paper", "runs/paper_generated",
       "--smoke", "runs/smoke", check=False)
sh(sys.executable, "tools/publish_results.py", "--message", MESSAGE)'''


def _lines(text: str):
    parts = text.split("\n")
    return [p + "\n" for p in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def _md(t):
    return {"cell_type": "markdown", "metadata": {}, "source": _lines(t)}


def _code(t):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": _lines(t)}


def build(out: Path = ROOT / "panda_sync.ipynb") -> None:
    cells = [_md(INTRO), _md("## 1. Lấy code mới nhất"), _code(SETUP), _md(TASK_MD), _code(TASK),
             _md(STATUS_MD), _code(STATUS), _md(PUBLISH_MD), _code(PUBLISH)]
    nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python",
                                                      "name": "python3"}, "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    Path(out).write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    build()
    print("wrote", ROOT / "panda_sync.ipynb")
