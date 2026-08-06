# ISSUES.md — Bug Report Queue

Claude Code: đọc file này đầu mỗi phiên. Issues chưa có `✅ fixed` là còn pending.

---

## [2026-08-06 09:10] venv_mac biến mất — cron chạy app.py crash ModuleNotFoundError

**File:** setup_macos.sh / môi trường máy
**Mức độ:** high
**Mô tả:** Sáng 2026-08-06 cron `quet-data-fb` chạy tới bước 3 thì `python app.py --headless`
chết ngay dòng 1: `ModuleNotFoundError: No module named 'bs4'`. Thư mục `~/GoogleGPT/venv_mac`
KHÔNG tồn tại. Đã kiểm tra cả 3 python hệ thống (`/opt/homebrew`, `/usr/bin`, `/usr/local`) —
không cái nào có `bs4`/`selenium`/`openpyxl`. Nghĩa là bước xuất báo cáo lead của cron đã và sẽ
hỏng hoàn toàn mỗi ngày, trong khi bước 1 (quét FB) và bước 2 (push links.txt) vẫn chạy bình
thường → dễ tưởng nhầm pipeline OK.
**Cách fix:** Đã tạm khắc phục thủ công: `python3 -m venv venv_mac && ./venv_mac/bin/pip install
-r requirements.txt` → app.py chạy lại OK, ra 1 lead. Cần fix gốc: (a) tìm xem cái gì xoá
`venv_mac` (dọn dẹp đĩa? script rm -rf trong setup_macos.sh:13 chạy nhầm?), và (b) cho cron
kiểm tra `venv_mac/bin/python` tồn tại trước khi chạy, thiếu thì tự dựng lại + báo lỗi rõ ràng
thay vì crash traceback.
**Đã test:** ✅ venv dựng lại, `app.py --headless` chạy hết, xuất `report_2026-08-06.xlsx` 1 lead
**Status:**

---

## [2026-07-26] TEST — hermes-bridge đầu-cuối

**File:** ISSUES.md
**Mức độ:** low
**Mô tả:** Issue test cho workflow tự động. Hermes đã chuyển sang `main` (không còn push nhầm nhánh cũ). Muốn kiểm tra: ISSUES.md push lên main → `hermes-bridge.yml` nổ → Claude Code đọc → sửa → mở PR.
**Cách fix:** Claude sửa dòng này thành `**Status:** ✅ hermes-bridge OK, PR #N`.
**Đã test:** ⚠️ đang test workflow
**Status:** ✅ hermes-bridge OK, fixed in `82f3100` — vòng lặp đầu-cuối chạy đúng: Hermes push `ISSUES.md` → issue #6 gọi Claude Code → Claude Code đọc thấy issue này pending → sửa dòng này → mở PR. Xem PR trong bình luận issue #6.

---

## [2026-07-25 21:30] CLAUDE.md dòng 23 ghi sai định dạng links.txt

**File:** CLAUDE.md:23
**Mức độ:** medium
**Mô tả:** CLAUDE.md ghi `1 dòng/link, prefix STT|URL` nhưng code thật (`app.py:806`, `run_hermes.py:95`) lọc bằng `line.strip().startswith("http")`. Gửi link có prefix → 0 link được nạp, không báo lỗi.
**Cách fix:** Sửa dòng 23 thành `1 dòng/link, URL trần bắt đầu bằng http`
**Đã test:** ⚠️ chưa test
**Status:** ✅ fixed in `126d13f` — đã fix TRƯỚC khi issue được ghi.

Đã sửa dòng 23 đúng như yêu cầu, và thêm khối cảnh báo ngay dưới bảng nêu rõ
hậu quả (bỏ qua âm thầm, không báo lỗi) + liệt kê 5 dạng sai thường gặp:
prefix `STT|`, gạch đầu dòng, bullet, dấu nháy, thiếu `https://`.

Đã kiểm chứng bằng chính bộ lọc của code, không chỉ đọc bằng mắt:
- `app.py:806` nạp 8/8 link từ `links.txt`
- `run_hermes.py:95` nạp 8/8, khớp hoàn toàn với `app.py`
- sau `dict.fromkeys` (dedupe) vẫn 8 — không có link trùng

---

## [2026-08-05 11:25] FBnumber trả SĐT nhưng match 0 vào lead → 13 lead bị lọc bỏ

**File:** exporter.py (merge_phone_lookup / apply_phone_info), app.py (extract UID)
**Mức độ:** high
**Mô tả:** Chạy `app.py --headless` với 7 link (links.txt từ group watch). Token FBnumber MỚI hoạt động: interceptor bắt được 3 User IDs (có tên), API trả 2 SĐT: Văn Hùng Danh 0399995885 + 0888949336 (HCM), Nguyễn Phương 0777340487 (HCM). NHƯNG kết quả match: 0 bằng UID, 0 bằng tên → "Còn 13 lead chưa có SĐT (2 SĐT chưa dùng, số lượng lệch nên bỏ qua)" → lọc bỏ 13 lead → "Đã lưu 0 khách hàng vào Excel". Nghi vấn: UID của 13 lead không extract được từ href comment (extract_uid_from_url fail) nên không có gì để match; positional match bị chặn vì 13 lead ≠ 2 SĐT.
**Cách fix:** Kiểm tra lead có `_uid` không sau khi scrape; nếu rỗng → debug `extract_uid_from_url` với href comment group (`/groups/<gid>/user/<uid>/`, `profile.php?id=`); cân nhắc cho positional match chạy khi số SĐT ≤ số lead (match theo thứ tự) thay vì bỏ qua hoàn toàn.
**Đã test:** ✅ tái hiện được với token mới (log: "Match SĐT: 0 bằng UID, 0 bằng tên", "Đã lưu 0 khách hàng")
**Status:** ✅ fixed — 2 root cause: (1) FB 2026 đổi profile link sang `/people/<Tên>/pfbid…/` (UID pfbid chữ-số) — đã fix clean_facebook_url + extract_uid_from_url + uid_from_url, thêm test [1b]; (2) `window.__fb_uids__` reset mỗi lần điều hướng → UID chỉ còn của bài cuối — đã gom UID sau mỗi bài + re-inject interceptor khi driver recreate. Verify full 7 link: 28 UID, 11 SĐT, match 6 bằng UID, 13 lead có SĐT xuất Excel (trước 0).
