"""
config.py — Single source of truth cho toàn bộ path & runtime settings.

Mọi script trong project (app.py, run_hermes.py, run_filter.py,
process_pipeline.py, run_clean.py) đều import từ đây.
Không script nào được hard-code path tuyệt đối nữa.

Hỗ trợ: macOS (Darwin), Windows, Linux.

Override bằng biến môi trường (đặt trong file .env hoặc export trong shell):
    HERMES_DRIVE_ROOT   -> đường dẫn tới "My Drive" (bỏ qua auto-detect)
    HERMES_RAW_DIR      -> ghi đè thư mục dữ liệu thô
    HERMES_FILTERED_DIR -> ghi đè thư mục dữ liệu đã lọc
    DEEPSEEK_API_KEY    -> API key DeepSeek
    CHROME_BINARY       -> đường dẫn Chrome tuỳ chỉnh
"""

from __future__ import annotations

import os
import platform
import socket
import sys
import unicodedata
from pathlib import Path

# ----------------------------------------------------------------------------
# 0. Nạp .env (không bắt buộc cài python-dotenv)
# ----------------------------------------------------------------------------
PROJECT_DIR: Path = Path(__file__).resolve().parent


def _load_dotenv(path: Path) -> None:
    """Parser .env tối giản: KEY=VALUE, bỏ qua comment và dòng trống."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv(PROJECT_DIR / ".env")

SYSTEM: str = platform.system()  # 'Darwin' | 'Windows' | 'Linux'
IS_MACOS: bool = SYSTEM == "Darwin"
IS_WINDOWS: bool = SYSTEM == "Windows"


# ----------------------------------------------------------------------------
# 1. Google Drive root — auto-detect theo từng OS
# ----------------------------------------------------------------------------
def _drive_candidates() -> list[Path]:
    home = Path.home()

    if IS_MACOS:
        # Drive for desktop v60+ mount tại ~/Library/CloudStorage/GoogleDrive-<email>/My Drive
        cloud = home / "Library" / "CloudStorage"
        found = sorted(cloud.glob("GoogleDrive-*/My Drive")) if cloud.is_dir() else []
        return [
            *found,
            Path("/Volumes/GoogleDrive/My Drive"),   # bản Drive cũ
            home / "Google Drive" / "My Drive",
            home / "Google Drive",
        ]

    if IS_WINDOWS:
        return [Path(f"{letter}:/My Drive") for letter in "GHIJKL"]

    return [home / "GoogleDrive", home / "Google Drive"]


def _detect_drive_root() -> tuple[Path, bool]:
    """Trả về (drive_root, is_real_drive)."""
    override = os.getenv("HERMES_DRIVE_ROOT")
    if override:
        return Path(override).expanduser().resolve(), True

    for candidate in _drive_candidates():
        if candidate.is_dir():
            return candidate.resolve(), True

    # Fallback: chạy hoàn toàn local, không phụ thuộc Drive.
    return (PROJECT_DIR / "drive_local").resolve(), False


DRIVE_ROOT, DRIVE_MOUNTED = _detect_drive_root()


def _nfc(text: str) -> str:
    """macOS/APFS lưu tên file dạng NFD; chuẩn hoá NFC để so sánh nhất quán."""
    return unicodedata.normalize("NFC", text)


PATH_RAW_DIR: Path = Path(
    os.getenv("HERMES_RAW_DIR") or DRIVE_ROOT / _nfc("Hermes")
)
PATH_FILTERED_DIR: Path = Path(
    os.getenv("HERMES_FILTERED_DIR") or DRIVE_ROOT / _nfc("Đã Lọc")
)

# ----------------------------------------------------------------------------
# 2. File I/O trong project
# ----------------------------------------------------------------------------
LINKS_FILE: Path = PROJECT_DIR / "links.txt"
SCRAPER_EXCEL: Path = PROJECT_DIR / "facebook_comments_result.xlsx"
RAW_COMMENTS_FILE: Path = PATH_RAW_DIR / "raw_comments.txt"
FILTERED_EXCEL: Path = PATH_FILTERED_DIR / "khach_hang_tiem_nang.xlsx"
PIPELINE_LOG: Path = PATH_RAW_DIR / "pipeline_log.txt"
DEBUG_DIR: Path = PROJECT_DIR / "debug"

# ----------------------------------------------------------------------------
# 3. Chrome / Selenium
# ----------------------------------------------------------------------------
EXTENSION_DIR: Path = PROJECT_DIR / "Ten_Thu_Muc_Extension"
CHROME_PROFILE_DIR: Path = PROJECT_DIR / "FB_Profile"

_CHROME_BINARIES = {
    "Darwin": [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        str(Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    ],
    "Windows": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ],
    "Linux": ["/usr/bin/google-chrome", "/usr/bin/chromium-browser"],
}


def detect_chrome_binary() -> str | None:
    """None => để Selenium Manager tự tìm (khuyến nghị với Selenium >= 4.6)."""
    override = os.getenv("CHROME_BINARY")
    if override:
        return override
    for path in _CHROME_BINARIES.get(SYSTEM, []):
        if Path(path).exists():
            return path
    return None


def free_port() -> int:
    """Cấp port trống thay vì hard-code 9222 (tránh xung đột khi chạy song song)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


# ----------------------------------------------------------------------------
# 4. Runtime
# ----------------------------------------------------------------------------
PYTHON_BIN: str = sys.executable          # thay cho "py" (chỉ có trên Windows)
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")


def ensure_dirs() -> None:
    """Tạo các thư mục output. Gọi ở đầu mỗi entrypoint."""
    for directory in (PATH_RAW_DIR, PATH_FILTERED_DIR, DEBUG_DIR, CHROME_PROFILE_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def describe() -> str:
    return (
        f"OS            : {SYSTEM}\n"
        f"Python        : {PYTHON_BIN}\n"
        f"Project       : {PROJECT_DIR}\n"
        f"Drive root    : {DRIVE_ROOT} "
        f"({'đã mount' if DRIVE_MOUNTED else 'KHÔNG thấy Drive -> dùng thư mục local'})\n"
        f"Raw dir       : {PATH_RAW_DIR}\n"
        f"Filtered dir  : {PATH_FILTERED_DIR}\n"
        f"Extension     : {EXTENSION_DIR} "
        f"({'OK' if EXTENSION_DIR.is_dir() else 'không tìm thấy — sẽ bỏ qua'})\n"
        f"Chrome binary : {detect_chrome_binary() or 'auto (Selenium Manager)'}\n"
        f"DeepSeek key  : {'đã cấu hình' if DEEPSEEK_API_KEY else 'CHƯA có -> dùng fallback keyword'}"
    )


if __name__ == "__main__":
    print(describe())
