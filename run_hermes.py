"""
run_hermes.py — Orchestrator cho pipeline Hermes.

Đa nền tảng: macOS / Windows / Linux. Toàn bộ path lấy từ config.py.

Thay đổi so với bản Windows:
  1. Bỏ "py" + shell=True  -> dùng sys.executable, list args, không shell.
  2. Bỏ path ổ G hard-code -> config.PATH_RAW_DIR / config.PATH_FILTERED_DIR.
  3. Sửa hợp đồng dữ liệu   -> app.py xuất .xlsx (không phải
     facebook_comments_data.txt), run_hermes đọc đúng file đó.
  4. API key đọc từ env / .env, không nhúng trong source.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import requests

import config
from exporter import norm_phone

# Cột do app.py xuất ra — PHẢI khớp exporter.COLUMNS, nếu không df.get() rơi
# vào giá trị mặc định và mọi dòng đều ra "N/A".
COL_NAME = "Tên KH"
COL_COMMENT = "Comment"
COL_PHONE = "SĐT"
COL_USER_LINK = "Facebook"
COL_POST_LINK = "Link bài viết"
COL_TIME = "Ngày tìm"

PHONE_RE = re.compile(r"(?:(?:\+?84|0)(?:3|5|7|8|9)\d{8})")
FALLBACK_KEYWORDS = (
    "inbox", "tư vấn", "bao nhiêu", "giá", "ship", "mua", "chốt", "ib", "nhiêu",
)


# ============================================================================
# SKILLS
# ============================================================================
class HermesSkills:
    # ------------------------------------------------------------------ 0 ---
    @staticmethod
    def skill_lay_link_tu_drive(drive_url: str) -> bool:
        """[SKILL 0] Tải file chứa link từ Google Drive -> links.txt"""
        print("\n[SKILL 0] Đang xử lý link Google Drive...")

        match = re.search(r"/d/([a-zA-Z0-9\-_]+)", drive_url)
        if match:
            file_id = match.group(1)
        elif "id=" in drive_url:
            file_id = drive_url.split("id=")[1].split("&")[0]
        else:
            print("LỖI: Link Google Drive sai định dạng, không tìm thấy File ID.")
            return False

        download_url = f"https://docs.google.com/uc?export=download&id={file_id}"
        try:
            response = requests.get(download_url, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"LỖI khi tải file: {exc}")
            return False

        new_links = [
            line.strip()
            for line in response.text.splitlines()
            if line.strip() and "facebook.com" in line
        ]
        if not new_links:
            print("LỖI: File tải về không chứa link Facebook hợp lệ.")
            return False

        config.LINKS_FILE.write_text("\n".join(new_links) + "\n", encoding="utf-8")
        print(f"[OK] Đã nạp {len(new_links)} link vào '{config.LINKS_FILE}'")
        return True

    # ------------------------------------------------------------------ 1 ---
    @staticmethod
    def skill_read_and_scrape(headless=False) -> bool:
        """[SKILL 1] Đọc links.txt -> gọi app.py từng link -> gom vào raw_comments.txt"""
        if not config.LINKS_FILE.exists():
            print(f"LỖI SKILL 1: Không tìm thấy '{config.LINKS_FILE}'.")
            return False

        links = [
            line.strip()
            for line in config.LINKS_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("http")
        ]
        links = list(dict.fromkeys(links))  # khử trùng lặp, giữ thứ tự

        if not links:
            print("LỖI SKILL 1: Danh sách link trống.")
            return False

        config.ensure_dirs()
        if not config.DRIVE_MOUNTED:
            print(f"[CẢNH BÁO] Không thấy Google Drive. Ghi tạm vào: {config.DRIVE_ROOT}")

        print(f"\n[SKILL 1] Bắt đầu quét {len(links)} link...")
        tmp_excel = config.PROJECT_DIR / "_hermes_tmp_scrape.xlsx"
        total_rows = 0

        for index, link in enumerate(links, 1):
            print(f"-> [{index}/{len(links)}] {link}")
            tmp_excel.unlink(missing_ok=True)

            cmd = [config.PYTHON_BIN, "app.py", link, "--out", str(tmp_excel)]
            if headless:
                cmd.append("--headless")

            result = subprocess.run(
                cmd,
                cwd=str(config.PROJECT_DIR),
                check=False,
            )
            if result.returncode != 0:
                print(f"   [BỎ QUA] app.py thoát với mã {result.returncode}")
                continue

            rows = HermesSkills._append_raw(tmp_excel, link)
            total_rows += rows
            print(f"   -> thu được {rows} bình luận")

            if index < len(links):
                time.sleep(3)

        tmp_excel.unlink(missing_ok=True)
        print(f"[SKILL 1 XONG] Tổng {total_rows} bình luận -> {config.RAW_COMMENTS_FILE}\n")
        return total_rows > 0

    @staticmethod
    def _append_raw(excel_path: Path, source_link: str) -> int:
        """Chuyển output .xlsx của app.py sang định dạng raw text tích luỹ."""
        if not excel_path.exists():
            return 0
        try:
            # dtype=str: khong de pandas ep cot SĐT thanh float
            # ("0776791717" -> 776791717.0, mat so 0 dau va them ".0").
            df = pd.read_excel(excel_path, dtype=str)
        except Exception as exc:
            print(f"   [LỖI] Không đọc được {excel_path.name}: {exc}")
            return 0
        if df.empty:
            return 0

        config.RAW_COMMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%d/%m/%Y %H:%M:%S")

        with config.RAW_COMMENTS_FILE.open("a", encoding="utf-8") as dest:
            dest.write(f"\n=== BÀI VIẾT QUÉT NGÀY {stamp} ===\n")
            dest.write(f"Link bài gốc: {source_link}\n\n")
            for _, row in df.iterrows():
                comment = str(row.get(COL_COMMENT, "")).strip()
                if not comment or comment.lower() == "nan":
                    continue
                # Ưu tiên cột SĐT (kết quả FBnumber, đã chuẩn hoá giữ số 0 đầu);
                # chỉ dò regex trên text comment khi cột đó rỗng.
                phone = norm_phone(row.get(COL_PHONE, ""))
                if not phone:
                    m = PHONE_RE.search(comment)
                    phone = norm_phone(m.group(0)) if m else "N/A"

                dest.write(f"Name: {row.get(COL_NAME, 'N/A')}\n")
                dest.write(f"Comment: {comment}\n")
                dest.write(f"User Link: {row.get(COL_USER_LINK, 'N/A')}\n")
                dest.write(f"Phone: {phone}\n")
                dest.write(f"Time: {row.get(COL_TIME, 'N/A')}\n")
                dest.write("-" * 40 + "\n")
        return len(df)

    # ------------------------------------------------------------------ 2 ---
    @staticmethod
    def skill_deepseek_filter() -> list:
        """[SKILL 2] Đọc raw_comments.txt -> DeepSeek phân loại nhu cầu mua"""
        if not config.RAW_COMMENTS_FILE.exists():
            print(f"LỖI SKILL 2: Chưa có '{config.RAW_COMMENTS_FILE}'.")
            return []

        content = config.RAW_COMMENTS_FILE.read_text(encoding="utf-8")
        parsed = []

        for block in content.split("-" * 40):
            comment_match = re.search(r"Comment:\s*(.*)", block)
            link_match = re.search(r"User Link:\s*(.*)", block)
            if not (comment_match and link_match):
                continue
            comment = comment_match.group(1).strip()
            user_link = link_match.group(1).strip()
            if not comment or not user_link:
                continue
            phone_match = re.search(r"Phone:\s*(.*)", block)
            name_match = re.search(r"Name:\s*(.*)", block)
            parsed.append({
                "name": name_match.group(1).strip() if name_match else "N/A",
                "comment": comment,
                "user_link": user_link,
                "phone": phone_match.group(1).strip() if phone_match else "N/A",
            })

        # Khử trùng lặp theo (link người dùng + nội dung comment)
        seen = set()
        unique = []
        for item in parsed:
            key = (item["user_link"], item["comment"])
            if key not in seen:
                seen.add(key)
                unique.append(item)

        if not unique:
            print("LỖI SKILL 2: Dữ liệu thô trống hoặc sai cấu trúc.")
            return []

        use_api = bool(config.DEEPSEEK_API_KEY)
        mode = "DeepSeek API" if use_api else "fallback keyword (chưa có API key)"
        print(f"\n[SKILL 2] Phân tích {len(unique)} bình luận — chế độ: {mode}")

        session = requests.Session() if use_api else None
        filtered = []
        for index, item in enumerate(unique, 1):
            print(f" -> {index}/{len(unique)}", end="\r")
            if HermesSkills._is_lead(item["comment"], session):
                filtered.append({
                    "Tên FB": item["name"],
                    "Comment": item["comment"],
                    "Link Người Comment": item["user_link"],
                    "Số điện thoại": item["phone"],
                })

        print(f"\n[SKILL 2 XONG] {len(filtered)} khách hàng tiềm năng.\n")
        return filtered

    @staticmethod
    def _is_lead(comment: str, session) -> bool:
        lowered = comment.lower()
        if session is None:
            return any(kw in lowered for kw in FALLBACK_KEYWORDS)

        prompt = (
            f"Phân tích bình luận: '{comment}'. Đây có phải câu hỏi/yêu cầu liên quan "
            f"đến: xin giá, bao nhiêu, tư vấn, inbox, ship, mua hàng không? "
            f"Chỉ trả lời 'YES' hoặc 'NO'."
        )
        try:
            response = session.post(
                f"{config.DEEPSEEK_BASE_URL}/chat/completions",
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                },
                headers={
                    "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
            response.raise_for_status()
            answer = response.json()["choices"][0]["message"]["content"]
            return "YES" in answer.strip().upper()
        except Exception as exc:
            # Fail-open sang keyword thay vì mất dữ liệu, nhưng log rõ nguyên nhân
            print(f"\n   [API lỗi -> fallback keyword] {exc}")
            return any(kw in lowered for kw in FALLBACK_KEYWORDS)

    # ------------------------------------------------------------------ 3 ---
    @staticmethod
    def skill_export_excel(data_list: list) -> bool:
        """[SKILL 3] Xuất Excel vào thư mục Đã Lọc (ghi tạm rồi replace)."""
        if not data_list:
            print("LỖI SKILL 3: Không có dữ liệu để xuất.")
            return False

        config.PATH_FILTERED_DIR.mkdir(parents=True, exist_ok=True)
        target = config.PATH_FILTERED_DIR / "comments_da_loc.xlsx"
        tmp = target.with_name(target.stem + "_tmp.xlsx")

        df = pd.DataFrame(data_list)
        # SĐT phải là text: pandas/Excel sẽ nuốt số 0 đầu (0912... -> 912...)
        if "Số điện thoại" in df.columns:
            df["Số điện thoại"] = df["Số điện thoại"].astype("string")

        try:
            df.to_excel(tmp, index=False, engine="openpyxl")
            os.replace(tmp, target)
        except PermissionError:
            print("[LỖI] File Excel đang mở. Hãy đóng file rồi chạy lại.")
            return False
        except Exception as exc:
            print(f"[LỖI] Ghi Excel thất bại: {exc}")
            return False
        finally:
            tmp.unlink(missing_ok=True)

        print(f"[SKILL 3 XONG] Đã lưu: {target}\n")
        return True


# ============================================================================
# CONSOLE
# ============================================================================
MENU = {
    "skill_lay_link_tu_drive": "Tải link từ Google Drive về links.txt",
    "skill_cao_du_lieu": "Quét bình luận từ links.txt",
    "skill_loc_deepseek": "Lọc bằng AI và xuất Excel",
    "skill_toan_nang": "Chạy toàn bộ chuỗi",
    "config": "In cấu hình path đang dùng",
    "exit": "Thoát",
}


def run_console() -> None:
    print("=" * 62)
    print("            HERMES AUTOMATION — SKILL INTERFACE")
    print("=" * 62)
    print(config.describe())
    print("-" * 62)
    for name, desc in MENU.items():
        print(f"  {name:<26} -> {desc}")
    print("=" * 62)

    skills = HermesSkills()

    while True:
        try:
            choice = input("\nNhập tên Skill: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nThoát.")
            return

        if choice == "exit":
            print("Đang tắt hệ thống.")
            return
        if choice == "config":
            print(config.describe())
        elif choice == "skill_lay_link_tu_drive":
            skills.skill_lay_link_tu_drive(input("Dán link Google Drive: ").strip())
        elif choice == "skill_cao_du_lieu":
            headless = input("Chạy ẩn (headless)? (y/N): ").strip().lower() == 'y'
            skills.skill_read_and_scrape(headless=headless)
        elif choice == "skill_loc_deepseek":
            skills.skill_export_excel(skills.skill_deepseek_filter())
        elif choice == "skill_toan_nang":
            headless = input("Chạy ẩn (headless)? (y/N): ").strip().lower() == 'y'
            print("\\n>>> BẮT ĐẦU CHUỖI TỰ ĐỘNG <<<")
            if skills.skill_read_and_scrape(headless=headless):
                skills.skill_export_excel(skills.skill_deepseek_filter())
            print(">>> HOÀN THÀNH <<<")
        else:
            print("Tên skill không hợp lệ.")


if __name__ == "__main__":
    # Cho phép chạy không tương tác (Hermes agent gọi qua Telegram):
    #   python run_hermes.py skill_toan_nang
    #   python run_hermes.py skill_toan_nang --headless
    if len(sys.argv) > 1:
        headless = "--headless" in sys.argv
        # Loại bỏ --headless khỏi args để không ảnh hưởng so sánh command
        clean_argv = [a for a in sys.argv[1:] if a != "--headless"]
        command = clean_argv[0] if clean_argv else ""
        skills = HermesSkills()
        if command == "skill_cao_du_lieu":
            skills.skill_read_and_scrape(headless=headless)
        elif command == "skill_loc_deepseek":
            skills.skill_export_excel(skills.skill_deepseek_filter())
        elif command == "skill_toan_nang":
            if skills.skill_read_and_scrape(headless=headless):
                skills.skill_export_excel(skills.skill_deepseek_filter())
        elif command == "config":
            print(config.describe())
        else:
            print(f"Lệnh không hợp lệ: {command}")
            sys.exit(1)
    else:
        run_console()
