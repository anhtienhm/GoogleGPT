# Chạy Hermes / GoogleGPT_Tool trên macOS

## 1. Cài đặt (một lần)

```bash
cd ~/Desktop/GoogleGPT_Tool     # hoặc thư mục bạn để project

chmod +x setup_macos.sh
./setup_macos.sh
```

Script sẽ: tạo `venv_mac`, cài dependency, kiểm tra Chrome, tạo `.env`, in cấu hình path.

> **Quan trọng:** thư mục `venv_worm/` trong file zip là venv Windows (chứa `.pyd`,
> `.dll`, `Lib/site-packages`). macOS **không dùng lại được** — bắt buộc tạo venv mới.
> Xoá nó đi: `rm -rf venv_worm`

## 2. Điền API key

```bash
cp .env.example .env
nano .env        # điền DEEPSEEK_API_KEY=sk-...
```

`.env` đã có trong `.gitignore`, không bị commit lên git.

## 3. Kiểm tra path trước khi chạy

```bash
source venv_mac/bin/activate
python run_hermes.py config
```

Dòng `Drive root` phải trỏ đúng vào Google Drive. Nếu sai, đặt thủ công trong `.env`:

```
HERMES_DRIVE_ROOT=/Users/<user>/Library/CloudStorage/GoogleDrive-<email>/My Drive
```

Tìm đường dẫn thật:

```bash
ls ~/Library/CloudStorage/
```

## 4. Chạy

```bash
python run_hermes.py                    # menu tương tác
python run_hermes.py skill_cao_du_lieu  # không tương tác (cho Hermes agent / Telegram)
python run_hermes.py skill_toan_nang
```

Lần chạy đầu Chrome sẽ mở ra — tự đăng nhập Facebook một lần, session được
lưu trong `FB_Profile/` cho các lần sau.

---

## Bảng đối chiếu Windows → macOS

| Hạng mục | Windows (cũ) | macOS (mới) |
|---|---|---|
| Interpreter | `py` | `sys.executable` qua `config.PYTHON_BIN` |
| Gọi subprocess | `shell=True` + list | list args, **không** shell |
| Google Drive | `G:\My Drive` | `~/Library/CloudStorage/GoogleDrive-<email>/My Drive` (auto-detect) |
| Thư mục project | `C:\Users\Admin\Desktop\WormGPT_Tool` | `config.PROJECT_DIR` (tương đối) |
| Extension Chrome | `...\Extension_Folder` | `./Ten_Thu_Muc_Extension` |
| venv | `venv_worm\Scripts\activate` | `source venv_mac/bin/activate` |
| Hermes agent path | `%LOCALAPPDATA%\hermes\hermes-agent` | lọc theo pattern, không hard-code |
| Chrome binary | auto | `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` |

## Lệnh Hermes agent trên macOS

Trong `Ket-noi-hermes-terminal.txt`, thay các lệnh Windows:

```
# Cũ (Windows)
cd C:\Users\Admin\Desktop\WormGPT_Tool
.\venv_worm\Scripts\Activate.ps1
python app.py

# Mới (macOS)
cd ~/Desktop/GoogleGPT_Tool
source venv_mac/bin/activate
python run_hermes.py skill_toan_nang
```

## Lỗi thường gặp trên macOS

| Lỗi | Nguyên nhân | Xử lý |
|---|---|---|
| `FileNotFoundError: 'py'` | Windows launcher không có trên macOS | Đã fix — dùng `config.PYTHON_BIN` |
| `SyntaxError: invalid non-printable character U+FEFF` | `run_clean.py` đọc BOM của `app.py` | Đã fix — `encoding='utf-8-sig'` |
| `ModuleNotFoundError: requests / openpyxl` | Thiếu trong venv gốc | `pip install -r requirements.txt` |
| `SessionNotCreatedException` | Chrome đang chạy với cùng `--user-data-dir` | Đóng hết Chrome hoặc dùng profile riêng |
| `“Google Chrome.app” cannot be opened` | Gatekeeper | `xattr -dr com.apple.quarantine "/Applications/Google Chrome.app"` |
| Ghi vào `Đã Lọc` thất bại | Drive chưa sync / tên có dấu | Đặt `HERMES_FILTERED_DIR` sang tên ASCII |
| Chrome không mở được | Chưa cấp quyền Automation | System Settings → Privacy & Security → Automation |
