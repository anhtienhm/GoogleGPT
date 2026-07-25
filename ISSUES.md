# ISSUES.md — Bug Report Queue

Claude Code: đọc file này đầu mỗi phiên. Issues chưa có `✅ fixed` là còn pending.

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

## [2026-07-25 21:45] TEST — Claude đọc được chưa?

**File:** ISSUES.md
**Mức độ:** low
**Mô tả:** Đây là issue test. Hermes muốn kiểm tra workflow tự động: ghi ISSUES.md → push → Claude Code đọc → phản hồi. Nếu Claude đọc được, reply bằng cách sửa dòng này thành `**Status:** ✅ seen by Claude — workflow OK`.
**Cách fix:** Không cần fix code — chỉ cần confirm đã đọc được.
**Đã test:** ⚠️ chưa — đang test workflow

---
