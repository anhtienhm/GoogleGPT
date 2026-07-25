"""
run_clean.py — Chạy app.py với sys.path đã dọn sạch venv của Hermes agent.

Sửa cho macOS:
  1. Không hard-code C:\\Users\\Admin\\AppData\\Local\\hermes -> lọc theo pattern.
     macOS: ~/.local/share/hermes, ~/Library/Application Support/hermes,
            ~/.hermes, /opt/homebrew/lib/.../hermes
  2. Đọc app.py bằng 'utf-8-sig'. Bản cũ dùng 'utf-8' nên ký tự BOM (U+FEFF)
     đầu file lọt vào exec() -> SyntaxError: invalid non-printable character.
"""

import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent

# Loại mọi entry sys.path thuộc về Hermes agent, không phụ thuộc OS
HERMES_MARKERS = ("hermes-agent", os.sep + "hermes" + os.sep, os.sep + ".hermes")


def _is_hermes_path(path: str) -> bool:
    normalized = os.path.normpath(path).lower() + os.sep
    return any(marker.lower() in normalized for marker in HERMES_MARKERS)


sys.path = [p for p in sys.path if p and not _is_hermes_path(p)]

# Đảm bảo import được config.py / app.py của project
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

app_path = PROJECT_DIR / "app.py"
sys.argv = [str(app_path)] + sys.argv[1:]

source = app_path.read_text(encoding="utf-8-sig")  # <- utf-8-sig: bỏ BOM
exec(compile(source, str(app_path), "exec"), {"__name__": "__main__", "__file__": str(app_path)})
