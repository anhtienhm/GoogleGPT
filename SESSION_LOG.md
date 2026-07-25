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

**[#1](https://github.com/anhtienhm/GoogleGPT/pull/1)** — ✅ **đã merge** (`e8ac5ec`), gộp 11 commit vào `main`.
Đã chạy lại `test_exporter.py` trên đúng bản `main`: 8/8 pass.

**Codex review bắt được 1 regression thật** (`app.py:195`) — đã sửa ở `21a555c`.

Chính đoạn fallback tên `dir='auto'` khôi phục ở `9d81388` gây ra: khi article
không có thẻ `<a>` dùng được **và chỉ có duy nhất 1 đoạn text**, đoạn đó là nội
dung comment chứ không phải tên. Lấy làm `author_name` khiến vòng bóc nội dung
loại chính nó (`text == author_name`) → `comment_text` rỗng → trả `None` →
**lead bị bỏ im lặng**.

Nghịch lý: fallback sinh ra để *cứu* lead trong group, nhưng ở tình huống này
lại *làm mất* lead vốn dĩ vẫn được giữ với tên placeholder.

```
co fallback  : <div dir="auto">ib giá giúp mình</div>  ->  None
tat fallback : ->  {'Tên KH': 'Nguoi dung Facebook', 'Comment': 'ib giá giúp mình'}
```

Sửa: chỉ lấy làm tên khi còn ít nhất 1 đoạn khác làm nội dung. Đã thêm 4 assert
regression vào `test_exporter.py` nhóm 3.

> **Bài học:** fallback "cứu dữ liệu" cần kiểm tra cả trường hợp nó *làm mất*
> dữ liệu. Test cũ chỉ phủ ca 2 đoạn (tên + comment), không phủ ca 1 đoạn.

⚠️ **Repo chưa có CI** — 0 workflow, 0 check chạy trên PR. `python test_exporter.py`
là cổng kiểm tra duy nhất, phải chạy thủ công trước khi push.

### ⚠️ QUY TRÌNH ĐÃ ĐỔI — làm thẳng trên `main`, KHÔNG mở PR

Từ phiên này trở đi: sửa xong → chạy test → commit → **push thẳng lên `main`**.
Không tạo Pull Request nữa.

```bash
git checkout main
python test_exporter.py            # BAT BUOC, phai pass
bash .claude/hooks/auto-push.sh    # commit + push len main
```

Đã gỡ chặn `main` trong `auto-push.sh` (`c19181f`) — giữ nguyên thì mọi phiên
sau đều bị chặn ngay ở bước push. Muốn bật lại: `CLAUDE_AUTOPUSH_PROTECT_MAIN=1`.

> **Không có CI.** `test_exporter.py` là cổng kiểm tra **duy nhất**, và chỉ chạy
> khi được gọi thủ công. Push mà chưa chạy test là đẩy lỗi thẳng lên `main`,
> không có gì chặn lại. Lỗi Codex bắt được ở PR #1 cho thấy điều này không phải
> lo xa — bộ test cũ vẫn xanh 8/8 trong khi lỗi đã nằm sẵn trong code.

### Còn treo

Không còn việc nào chờ. `data-facebook` đã đưa biển báo deprecated lên `main`
(`55fadbd`, fast-forward) — cảnh báo giờ hiện ở trang chính của repo đó.

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
