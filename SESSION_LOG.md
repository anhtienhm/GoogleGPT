# SESSION_LOG.md — Nhật ký phiên làm việc

Claude Code ghi vào đây **cuối mỗi phiên**. Hermes `git pull` rồi đọc, không cần ai chuyển lời.

**Quy ước:** phiên mới nhất nằm **trên cùng**. Không sửa/xoá entry cũ.

---

## [2026-07-25] Hợp nhất về GoogleGPT + dựng workflow ISSUES/test

**Nhánh:** `claude/sync-googlegpt-features-m61u39`
**Commit:** `9d81388` → `0587782` (7 commit, +364 / −34, 8 file)
**Test:** ✅ `python test_exporter.py` — 8/8 nhóm pass
**Queue:** rỗng

### Kết quả

| Commit | Nội dung |
|---|---|
| `0587782` | `test_exporter.py` + pitfalls 6–8 + mục "Test & debug" |
| `511262d` | Đánh dấu issue `links.txt` đã fix |
| `76be87f` | *(Hermes)* thêm `ISSUES.md` + workflow |
| `126d13f` | `links.txt` 8 link + sửa định dạng trong `CLAUDE.md` |
| `954025f` | Cho phép commit `links.txt` |
| `59d2745` | Gỡ FBnumber khỏi `--headless`, hợp đồng cột Hermes, vá `auto-push.sh` |
| `9d81388` | Khôi phục dấu tiếng Việt (`TIME_PATTERN`, selector Reel), fallback tên |

### Lỗi đã sửa — đều hỏng ÂM THẦM

Điểm chung: không crash, không báo lỗi, chỉ ra dữ liệu rỗng hoặc thiếu. Rất dễ tưởng nhầm là "bài viết không có lead".

| Lỗi | Hậu quả trước khi sửa |
|---|---|
| `TIME_PATTERN` mất dấu tiếng Việt | FB render "2 giờ", "Vừa xong" → pattern không khớp gì → `is_junk()` không lọc được timestamp → timestamp lọt vào tên tác giả và comment |
| 4/4 selector `open_reel_comments()` mất dấu | FB render "Bình luận" → không mở được bảng bình luận Reel → **2 link reel trong `links.txt` ra 0 comment** |
| Fallback tên `dir='auto'` bị xoá | FB không render `<a>` cho tên trong group → mọi lead group đều là "Nguoi dung Facebook" |
| FBnumber gắn vào `--headless` | `run_hermes` mặc định không truyền cờ → không tra số → bộ lọc SĐT xoá sạch → **ra gần 0 dòng**. Mâu thuẫn với chính help text `--no-fbnumber` ("mặc định: có") |
| Tên cột `run_hermes.py` lệch `exporter.COLUMNS` | `raw_comments.txt` có `Name`/`User Link`/`Time` = `N/A` ở **mọi** dòng |
| `_append_raw` bỏ qua cột `SĐT` | Chỉ dò regex trên text comment, không đọc kết quả FBnumber |
| `pd.read_excel` không có `dtype=str` | pandas ép cột SĐT thành float: `"0776791717"` → `776791717.0` |
| `auto-push.sh` — 3 lỗi | Báo `exit 0` nhưng **không commit, không push**. Mọi phiên tin vào hook đều mất việc mà không biết |

### Cần biết

- **Không cần `--headless` nữa.** `python run_hermes.py skill_toan_nang` chạy được. Muốn tắt tra số thì dùng `--no-fbnumber`.
- **Tác dụng phụ:** chạy có GUI giờ cũng gọi API FBnumber → tốn quota. Debug thì thêm `--no-fbnumber`.
- **`data-facebook` đã ngừng dùng** (`55fadbd` — dựng biển báo ở README). Còn nguyên 3 lỗi trên, đều hỏng âm thầm. Đừng chạy.
- **`links.txt`** đã có 8 link: 2 reel, 5 post fanpage, 1 group. Kiểm chứng bằng bộ lọc thật của `app.py:806` và `run_hermes.py:95` — nạp 8/8.

### PR

**[#1](https://github.com/anhtienhm/GoogleGPT/pull/1)** — gộp 8 commit vào `main` (+462 / −34, 9 file).
Trạng thái: `open`, `mergeable_state: clean`, không xung đột.

⚠️ **Repo chưa có CI** — 0 workflow, 0 check chạy trên PR. `python test_exporter.py`
là cổng kiểm tra duy nhất, phải chạy thủ công trước khi push.

### Còn treo

| # | Việc | Chờ ai |
|---|---|---|
| 1 | Review + merge PR #1 | sư phụ |
| 2 | Biển báo deprecated của `data-facebook` đang nằm trên nhánh, **chưa vào `main`** → người xem trang chính chưa thấy cảnh báo. Mở PR cho repo đó? | sư phụ |

---

<!--
KHUON MAU CHO PHIEN SAU — copy phan duoi, dien vao, dat LEN TREN entry cu nhat.

## [YYYY-MM-DD] Tiêu đề ngắn

**Nhánh:** `...`
**Commit:** `abc1234` → `def5678` (N commit)
**Test:** ✅/❌ `python test_exporter.py`
**Queue:** rỗng / N issue pending

### Kết quả
| Commit | Nội dung |
|---|---|

### Cần biết
- ...

### Còn treo
| # | Việc | Chờ ai |
|---|---|---|
-->
