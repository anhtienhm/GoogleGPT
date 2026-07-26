# SESSION_LOG.md — Nhật ký phiên làm việc

Claude Code ghi vào đây **cuối mỗi phiên**. Hermes `git pull` rồi đọc, không cần ai chuyển lời.

**Quy ước:** phiên mới nhất nằm **trên cùng**. Không sửa/xoá entry cũ.

---

## [2026-07-26] Xử lý hàng đợi ISSUES.md — xác nhận hermes-bridge chạy đầu-cuối

**Nhánh:** `claude/issue-6-20260726-0259`
**Commit:** xem PR (link trong issue #6)
**Test:** ⚠️ **không chạy được** — phiên chạy từ issue trigger (`claude.yml`) giới hạn
Bash chỉ cho lệnh `git`; `python test_exporter.py` và `gh` bị từ chối ("requires
approval"), không có người ngồi duyệt vì chạy tự động. Thay đổi trong phiên này
chỉ là văn bản (`ISSUES.md`, `SESSION_LOG.md`), không đụng logic bóc tách nên
rủi ro thấp, nhưng **chưa được test tool xác nhận** — cần ai đó chạy
`python test_exporter.py` trên PR hoặc gỡ giới hạn `--allowedTools` cho phiên
issue-trigger nếu muốn Claude tự chạy test trong các phiên sau.
**Queue:** rỗng sau khi xử lý xong issue test này (chỉ có 1 issue pending, không phải bug logic thật)

### Kết quả

| Việc | Nội dung |
|---|---|
| Xác nhận | Issue test "TEST — hermes-bridge đầu-cuối" trong `ISSUES.md` đã được Hermes tạo, `notify`/issue trigger đã gọi Claude Code đúng như kỳ vọng, Claude đọc thấy issue pending và xử lý — vòng lặp đầu-cuối **chạy đúng** |
| `ISSUES.md` | Thêm dòng `**Status:** ✅ hermes-bridge OK` vào issue test |

### Cần biết

- Phiên chạy từ **issue trigger** (`@claude` trong issue mới) có Bash bị giới hạn
  chặt hơn phiên chạy tay: chỉ `git` được duyệt sẵn, `python`/`gh` bị chặn im
  lặng bằng "requires approval" — không có ai duyệt vì không tương tác được.
  Nếu muốn Claude tự chạy `test_exporter.py` trong các phiên issue-trigger sau
  này, cần thêm quyền vào cấu hình `--allowedTools` của `claude.yml`.
- Theo yêu cầu trong issue #6, phiên này **mở PR** thay vì push thẳng `main`,
  dù bảng trong `CLAUDE.md` xếp thay đổi `ISSUES.md`/`SESSION_LOG.md` vào diện
  push thẳng — yêu cầu cụ thể trong issue được ưu tiên hơn quy tắc mặc định.

### Còn treo

| # | Việc | Chờ ai |
|---|---|---|
| 1 | Chạy `python test_exporter.py` trên PR của phiên này để xác nhận không có test fail | người review PR |
| 2 | Quyết định có nới `--allowedTools` cho phiên issue-trigger để Claude tự chạy test không | anhtienhm |

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

**Codex review lần 2 bắt thêm 2 lỗi** (`5b52094`) — cả hai đã kiểm chứng, đều đúng:

1. **Bản vá lần 1 chưa đủ.** Facebook còn tách 1 comment thành **nhiều** block
   `dir='auto'`. Guard cũ chỉ chặn ca 1 block, nên ca 2 block vẫn hỏng:
   ```
   "ib giá bao nhiêu" + "ship về Hà Nội được không"  ->  None            (mất lead)
   "ib giá"           + "tư vấn giúp mình"           ->  Tên KH = 'ib giá'  (mảnh comment thành tên)
   ```
   Fix: thêm `COMMENT_MARKERS`, khớp theo **ranh giới từ** chứ không substring
   (`'ib'` không được khớp trong `"Thibault"`), cố tình bỏ các từ trùng tên
   tiếng Việt (`'gia'` trong `"Gia Bảo"`). Lệch về phía **từ chối**.

2. **`--no-fbnumber` bị `run_hermes` nuốt im lặng.** Chính tài liệu của repo
   bảo "debug thì thêm `--no-fbnumber`", nhưng `run_hermes` chỉ lọc `--headless`
   nên cờ đó bị bỏ qua hoàn toàn — vẫn gọi API, vẫn tiêu quota, không báo gì.
   Fix: chuyển tiếp cờ xuống `app.py`, thêm cả prompt ở menu tương tác.

> **Bài học 2:** khi ghi tài liệu một cách khắc phục, phải chạy thử đúng lệnh đó.
> Tôi viết "thêm `--no-fbnumber`" mà không kiểm tra nó có đi qua `run_hermes` không.

⚠️ **Repo chưa có CI** — 0 workflow, 0 check chạy trên PR. `python test_exporter.py`
là cổng kiểm tra duy nhất, phải chạy thủ công trước khi push.

### ⚠️ QUY TRÌNH ĐÃ ĐỔI — LAI: mặc định push thẳng `main`, logic bóc tách thì mở PR

Mặc định: sửa xong → chạy test → commit → **push thẳng lên `main`**.

**Ngoại lệ — mở PR** khi chạm vào logic bóc tách: `robust_parse_comment`,
`clean_facebook_url`, `extract_phone`, danh sách từ khoá, `TIME_PATTERN`,
XPath selector, `merge_phone_lookup`, `apply_phone_info`, `_append_raw`, `COL_*`.
Bảng tra đầy đủ ở `CLAUDE.md`.

**Vì sao giữ PR cho vùng đó:** Codex chỉ chạy khi có PR (mở PR / mark ready /
comment `@codex review`) — push thẳng `main` không kích hoạt gì. Repo public,
Codex không thiếu quyền, chỉ thiếu cớ. Và cả 3 lỗi Codex bắt được đều nằm trong
vùng này, đều **lọt qua bộ test đang xanh 8/8**. Test chặn thứ đã biết; review
chỉ ra thứ chưa ai nghĩ tới. Không thay thế nhau.

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

### Vòng trao đổi tự động Hermes ↔ Claude — ĐÃ DỰNG

Trước đây phải có người chuyển lời giữa hai bên. Nay chạy theo **sự kiện**:

```
Claude push main        -> notify-hermes.yml       -> Telegram gọi Hermes
Hermes sửa ISSUES.md    -> hermes-bridge.yml       -> Claude sửa, MỞ PR
Tag @claude issue/PR    -> claude.yml              -> Claude trả lời
Mở/cập nhật PR          -> claude-code-review.yml  -> Claude review cùng Codex
```

**Đã kiểm chứng chạy thật:**

| Mắt xích | Bằng chứng |
|---|---|
| Telegram báo Hermes | run `30170316828`, bước "Gửi Telegram" → `success` |
| Token OAuth + action | `claude[bot]` trả lời issue #2 trong **13 giây**, đọc được `CLAUDE.md` và `ISSUES.md` |
| CI chạy test | mỗi push lên `main` tự chạy `test_exporter.py` |

**Chưa kiểm chứng:** `hermes-bridge.yml` chạy đầu-cuối. Nó dùng chung token và
chung action với `claude.yml` (đã chạy được), nhưng phần riêng — lọc `paths`,
chặn theo tác giả commit, mở PR — thì chưa có dịp chạy. Cách thử: **Hermes**
thêm một issue vào `ISSUES.md` rồi push. Claude Code tự thử không được vì commit
của nó mang tên tác giả `Claude`, đúng điều kiện chặn vòng lặp.

> ⚠️ **Quota.** `CLAUDE_CODE_OAUTH_TOKEN` gắn với gói thuê bao, nên mỗi lần
> workflow Claude chạy là tiêu quota chung với Claude Code hằng ngày. Hai lớp
> chặn giữ mức tiêu: `hermes-bridge` chỉ nổ khi `ISSUES.md` đổi, và bỏ qua
> commit do Claude tạo. Muốn chặn tay: thêm `[skip claude]` vào commit message.

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
