# Chạy Claude Code trên Panda

Mục tiêu: Claude Code chạy ngay trong Terminal của JupyterLab trên Panda. Nó tự clone repo, tự submit
job LTspice/Gemma, tự đọc kết quả và sửa lỗi. Nó làm theo `CLAUDE.md` ở gốc repo, file đó Claude tự đọc
khi khởi động.

Thay `hpham` bằng tên thư mục của bạn trong `/work` ở mọi lệnh dưới đây.

## Trước khi bắt đầu (đọc kỹ)

- **Notebook dùng chung cả team.** Cả team thấy cùng một JupyterLab, cùng `/work`, cùng terminal.
  Tài khoản Claude và token GitHub lưu trong `/work/hpham/.home` nên **người cùng team có thể dùng
  được**. `chmod 700` chỉ bảo vệ được nếu mỗi người có user riêng trong container, điều này chưa chắc.
  Vì thế:
  - dùng token GitHub **fine-grained, chỉ cho đúng repo này**, quyền ít nhất có thể, có hạn dùng ngắn;
  - xong việc thì đăng xuất Claude (`/logout`) và thu hồi token trên GitHub.
- **Hỏi admin CAIR trước**: chạy một AI agent trên Panda nghĩa là code, log và kết quả mô phỏng được
  gửi tới Anthropic. Nên xin phép trước khi dùng.
- Claude Code chạy trong terminal, nên dùng chung ~4 GB RAM với các kernel notebook của cả team. Đừng
  để nhiều phiên Claude chạy cùng lúc.

## Lần đầu (một lần)

### 1. Tạo token GitHub chỉ đọc repo này

Làm trên laptop: GitHub → Settings → Developer settings → Personal access tokens → **Fine-grained
tokens** → Generate new token.
- Repository access: **Only select repositories** → `piezo-topology-synthesis`.
- Permissions → Repository → **Contents: Read-only**. Chọn Read and write nếu muốn Claude push kết
  quả lên; nó vẫn chỉ push khi bạn bảo.
- Expiration: ngắn thôi, ví dụ 30 ngày.

Copy token lại. Chỉ bạn tự dán token vào terminal, đừng gửi nó cho Claude.

### 2. Mở Terminal trên Panda và cài Claude Code vào `/work`

Mở notebook như thường lệ (tunnel SSH qua narrows, theo USER-GUIDE), rồi **File → New → Terminal**:

```bash
mkdir -p /work/hpham/.home && chmod 700 /work/hpham/.home
export HOME=/work/hpham/.home
export PATH="$HOME/.local/bin:$PATH"
curl -fsSL https://claude.ai/install.sh | bash
claude --version
```

`HOME` được trỏ vào `/work` để Claude Code, phần đăng nhập và cấu hình **không mất khi notebook restart**.

Nếu `curl` không tải được (Panda chặn internet), dừng ở đây và hỏi admin CAIR có cho truy cập
`claude.ai` / `storage.googleapis.com` không. Nếu có Node.js ≥ 18 thì có thể thử
`npm install -g --prefix "$HOME/.local" @anthropic-ai/claude-code`.

### 3. Clone repo

```bash
cd /work/hpham
git config --global credential.helper "cache --timeout=28800"
git clone https://github.com/anphammmm/piezo-topology-synthesis.git
cd piezo-topology-synthesis
git checkout feat/v2-screen-size-paper
```

Khi git hỏi: Username là `anphammmm`, Password là **token** ở bước 1. Token chỉ nằm trong bộ nhớ 8 tiếng,
không ghi ra đĩa.

### 4. Đăng nhập Claude

```bash
source tools/panda_env.sh
claude
```

Lần đầu Claude in ra một đường link. Mở link đó trên laptop, đăng nhập tài khoản Claude của bạn, rồi
dán mã nhận được vào terminal.

## Mỗi lần làm việc

```bash
cd /work/hpham/piezo-topology-synthesis
source tools/panda_env.sh
claude
```

Rồi giao việc bằng lời, ví dụ:

- "Chạy smoke test rồi kiểm tra theo checklist trong README."
- "Chạy một lần đơn lẻ, đọc report.md và nói kết quả."
- "Chạy campaign cho paper, báo tiến độ."
- "Biểu đồ waveform bị trống, tìm nguyên nhân và sửa."

Claude submit job bằng `tools/panda_submit.py` (`gpus=0`, image `ltspice-cpu`). Job chạy tiếp kể cả
khi bạn đóng terminal hoặc tắt laptop. Mở lại thì `source tools/panda_env.sh`, chạy `claude`, rồi hỏi
"job tới đâu rồi?".

## Nếu có vấn đề

| Hiện tượng | Cách xử lý |
|---|---|
| `claude: command not found` sau khi notebook restart | chưa `source tools/panda_env.sh` |
| git hỏi lại token | token cache hết 8 tiếng, nhập lại |
| Claude đòi đăng nhập lại | `HOME` chưa trỏ vào `/work`: `source tools/panda_env.sh` |
| Notebook bị restart khi Claude đang chạy | thiếu RAM: tắt bớt kernel đang mở, chỉ chạy một phiên Claude |
| Muốn thu hồi quyền | GitHub → Settings → token → Revoke; trong Claude gõ `/logout` |
