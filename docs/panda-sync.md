# Chạy trên Panda, sửa code trên laptop, GitHub làm cầu nối

Panda vào được `github.com` nhưng bị chặn `claude.ai` và `api.anthropic.com` (kiểm tra ngày 2026-11-27),
nên Claude Code không chạy trực tiếp trên Panda được. Cách làm thay thế:

```
laptop (Claude)  --push code-->  GitHub  --pull-->  Panda (panda_sync.ipynb chạy job LTspice)
laptop (Claude)  <--fetch results--  GitHub  <--push nhánh results--  Panda
```

Bạn chỉ cần bấm chạy các ô trong `panda_sync.ipynb`. Không phải copy log nữa.

Thay `hpham` bằng tên thư mục của bạn trong `/work` ở mọi lệnh dưới đây.

## Lần đầu

### 1. Tạo token GitHub (trên laptop)

GitHub → Settings → Developer settings → Personal access tokens → **Fine-grained tokens** →
Generate new token:
- Repository access: **Only select repositories** → `piezo-topology-synthesis`
- Permissions → Repository permissions → **Contents: Read and write** (để đẩy kết quả lên nhánh `results`)
- Expiration: 30 ngày

Copy token lại. Không dán token vào chat.

### 2. Lưu token trên Panda

Trong JupyterLab: **File → New → Terminal**, chạy:

```bash
mkdir -p /work/hpham/.secrets && chmod 700 /work/hpham/.secrets
read -s -p "dán token rồi Enter: " T && printf %s "$T" > /work/hpham/.secrets/github_token && unset T
chmod 600 /work/hpham/.secrets/github_token && echo saved
```

Khi dán, token không hiện ra màn hình; đó là bình thường. Lưu ý: notebook dùng chung cả team và có thể
cùng một user Linux, nên người cùng team về nguyên tắc đọc được file này. Vì vậy token chỉ có quyền trên
đúng repo này và chỉ dùng được 30 ngày. Muốn thu hồi thì vào GitHub → Settings → token → Revoke.

### 3. Đặt notebook vào thư mục của bạn

Upload `panda_sync.ipynb` vào `/work/hpham/`, tức **thư mục của bạn, không phải bên trong repo**. Lấy file
này từ repo hoặc từ Claude.

## Mỗi lần dùng

Mở `/work/hpham/panda_sync.ipynb`:

1. **Ô 1**: lấy code mới nhất. Lần đầu nó tự clone repo về `/work/hpham/piezo-topology-synthesis`.
   Thấy dòng `ready` là được.
2. **Ô 2**: đặt `TASK` rồi chạy. Thứ tự nên làm: `"smoke"` → `"single"` → `"waves"` → `"campaign"`.
   Job chạy trên cụm; bạn có thể đóng trình duyệt.
3. **Ô 3**: xem tiến độ bất cứ lúc nào.
4. **Ô 4**: khi việc xong (hoặc muốn Claude xem giữa chừng), ghi vài chữ vào `MESSAGE` rồi chạy để đẩy
   kết quả lên GitHub.

Rồi nhắn Claude trên laptop: "đã đẩy kết quả smoke test". Claude tự lấy nhánh `results` về đọc, sửa code
nếu cần và push. Bạn chạy lại **ô 1** là có bản sửa.

## Nếu có vấn đề

| Hiện tượng | Cách xử lý |
|---|---|
| `chưa có token` ở ô 1 | làm bước 2 |
| `Authentication failed` / `403` | token sai, hết hạn hoặc thiếu quyền Contents → tạo lại ở bước 1 và lưu lại ở bước 2 |
| `Not possible to fast-forward` ở ô 1 | có file trong repo bị sửa trên Panda; nhắn Claude kèm output của ô 1 |
| `push failed` ở ô 4 | token chỉ có quyền đọc → cần **Read and write** |
| ô 2 báo `no module named gpu` | chạy notebook trong JupyterLab của Panda, không phải chỗ khác |
