#!/usr/bin/env bash
# auto-push.sh — Gọi sau mỗi lần sửa file.
# Tự retry, tự pull --rebase khi bị rejected, thoát im lặng khi tree sạch.
set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo "$(dirname "$0")/../..")"

# Kiểm tra git repo
if ! git rev-parse --git-dir >/dev/null 2>&1; then
    echo "[auto-push] Not a git repository, skipping." >&2
    exit 0
fi

# Đọc cấu hình từ env (nếu có)
AUTOPUSH_ALLOW_PROTECTED="${CLAUDE_AUTOPUSH_ALLOW_PROTECTED:-0}"

# Không có gì để push → im lặng thoát (gọi thừa vô hại)
if ! git diff --cached --quiet 2>/dev/null || ! git diff --quiet 2>/dev/null; then
    # Có thay đổi → add và commit
    git add -A
    git commit -m "auto-push: $(date '+%Y-%m-%d %H:%M')" || true
fi

# Kiểm tra staged changes
if git diff --cached --quiet 2>/dev/null; then
    # Khong co staged change -> thu push cac commit chua push.
    # @{u}..HEAD = so commit local di TRUOC remote (ahead).
    # HEAD..@{u} la chieu nguoc lai (behind) -> luon = 0 khi can push -> thoat nham.
    if git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
        if [ "$(git rev-list '@{u}..HEAD' 2>/dev/null | wc -l)" -eq 0 ]; then
            exit 0  # im lang thoat -- tree sach, khong co gi de push
        fi
    fi
    # Chua co upstream -> van chay tiep de push -u tao nhanh tren remote
fi

# Kiểm tra protected branch (main)
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" = "main" ] && [ "$AUTOPUSH_ALLOW_PROTECTED" != "1" ]; then
    echo "[auto-push] ERROR: main branch is protected. Set CLAUDE_AUTOPUSH_ALLOW_PROTECTED=1 to override (ask user first)." >&2
    exit 1
fi

# Push với auto-retry + rebase khi rejected
MAX_RETRIES=3
RETRY_DELAY=3
for i in $(seq 1 "$MAX_RETRIES"); do
    # Chi pull --rebase khi nhanh DA ton tai tren remote. Nhanh moi tinh thi
    # pull luon that bai -> truoc day khong bao gio push duoc nhanh moi.
    if git ls-remote --exit-code --heads origin "$CURRENT_BRANCH" >/dev/null 2>&1; then
        git pull --rebase origin "$CURRENT_BRANCH" 2>/dev/null || true
    fi
    if git push -u origin "$CURRENT_BRANCH" 2>/dev/null; then
        echo "[auto-push] OK — pushed to $CURRENT_BRANCH"
        exit 0
    fi
    if [ "$i" -lt "$MAX_RETRIES" ]; then
        sleep "$RETRY_DELAY"
    fi
done

# Hết retry → báo lỗi specific
echo "[auto-push] FAILED after $MAX_RETRIES attempts." >&2
if git ls-remote --exit-code origin "$CURRENT_BRANCH" >/dev/null 2>&1; then
    echo "[auto-push] Remote conflict: git pull --rebase failed. Do NOT use --force without asking the user." >&2
else
    echo "[auto-push] Permission denied or network error." >&2
fi
exit 1
