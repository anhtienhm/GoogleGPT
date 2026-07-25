# ISSUES.md — Bug Report Queue

Claude Code: đọc file này đầu mỗi phiên. Issues chưa có `✅ fixed` là còn pending.

---

## [2026-07-25 21:30] CLAUDE.md dòng 23 ghi sai định dạng links.txt

**File:** CLAUDE.md:23
**Mức độ:** medium
**Mô tả:** CLAUDE.md ghi `1 dòng/link, prefix STT|URL` nhưng code thật (`app.py:806`, `run_hermes.py:95`) lọc bằng `line.strip().startswith("http")`. Gửi link có prefix → 0 link được nạp, không báo lỗi.
**Cách fix:** Sửa dòng 23 thành `1 dòng/link, URL trần bắt đầu bằng http`
**Đã test:** ⚠️ chưa test

---
