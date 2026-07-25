#!/usr/bin/env bash
# setup_macos.sh — dựng môi trường chạy trên macOS
# Chạy: chmod +x setup_macos.sh && ./setup_macos.sh
set -euo pipefail

cd "$(dirname "$0")"

echo "==> 1/5 Kiểm tra Python 3"
command -v python3 >/dev/null || { echo "Chưa có python3. Cài: brew install python@3.12"; exit 1; }
python3 --version

echo "==> 2/5 Tạo venv mới (venv_worm của Windows KHÔNG dùng lại được)"
rm -rf venv_mac
python3 -m venv venv_mac
source venv_mac/bin/activate
python -m pip install --upgrade pip

echo "==> 3/5 Cài dependency"
pip install -r requirements.txt

echo "==> 4/5 Kiểm tra Google Chrome"
if [ -d "/Applications/Google Chrome.app" ]; then
  echo "    OK: /Applications/Google Chrome.app"
else
  echo "    CẢNH BÁO: chưa thấy Chrome. Cài: brew install --cask google-chrome"
fi

echo "==> 5/5 In cấu hình path"
[ -f .env ] || { cp .env.example .env; echo "    Đã tạo .env từ .env.example — nhớ điền DEEPSEEK_API_KEY"; }
python config.py

echo
echo "Xong. Dùng:"
echo "  source venv_mac/bin/activate"
echo "  python run_hermes.py            # menu tương tác"
echo "  python run_hermes.py config     # kiểm tra path"
echo "  python run_hermes.py skill_toan_nang"
