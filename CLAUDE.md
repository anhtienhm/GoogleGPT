# GoogleGPT — Facebook Lead Scraper

## Tổng quan

Pipeline quét comment Facebook, lọc lead có nhu cầu mua, tra SĐT qua FBnumber API, xuất Excel 15 cột.

```
URL post → scrape_one_post() → robust_parse_comment() → accumulate all_data
                                                             ↓
                                          FBnumber lookup → merge_phone_lookup()
                                                             ↓
                                          filter SĐT empty → save_excel() → .xlsx
```

## File chính

| File | Vai trò |
|------|---------|
| `app.py` | Scraper chính: Selenium headless, GraphQL interceptor, FBnumber API |
| `exporter.py` | Export engine: merge, lookup, save Excel (openpyxl) |
| `config.py` | Cấu hình: token FBnumber (`FB_NUMBER_TOKEN`), Chrome profile path, extension path |
| `.claude/hooks/auto-push.sh` | Auto-push script — chạy sau mỗi lần sửa file |
| `ISSUES.md` | Bug report queue — Hermes ghi bug, Claude Code đọc & fix |
| `SESSION_LOG.md` | Nhật ký phiên — Claude Code ghi cuối mỗi phiên, Hermes pull về đọc |
| `test_exporter.py` | Test regression 8 nhóm — chạy sau mỗi lần sửa code |
| `links.txt` | Danh sách URL bài viết — 1 dòng/link, **URL trần bắt đầu bằng `http`** |

> ⚠️ `app.py:806` và `run_hermes.py:95` đều lọc `line.strip().startswith("http")`.
> Dòng có prefix (`1|https://...`), gạch đầu dòng, bullet, dấu nháy, hay thiếu
> `https://` sẽ bị **bỏ qua âm thầm — không báo lỗi**. Sai định dạng = nạp 0 link
> mà không có thông báo nào.

## ⚠️ Bảo mật

- **Không commit thư mục `FB_Profile/`** — chứa session cookies Facebook cá nhân
- **`FB_NUMBER_TOKEN` trong `config.py`** — là token API thật, hardcode để tiện chạy CLI, nhưng cẩn thận khi share repo
- **Đã có trong `.gitignore`**: `.env`, `*.xlsx`, `FB_Profile*/`

## Quy trình — làm thẳng trên `main`, KHÔNG mở PR

**Không tạo Pull Request.** Sửa xong → chạy test → commit → push thẳng lên `main`.

```bash
git checkout main
# ... sua file ...
python test_exporter.py            # BAT BUOC, phai pass
bash .claude/hooks/auto-push.sh    # commit + push len main
```

`main` **không còn được bảo vệ** trong `auto-push.sh` — đây là quy ước đã chốt,
không phải nhầm lẫn. Muốn bật lại lớp bảo vệ thì đặt `CLAUDE_AUTOPUSH_PROTECT_MAIN=1`.

> Không có CI trên repo. `test_exporter.py` là cổng kiểm tra **duy nhất**, và
> nó chỉ chạy khi được gọi thủ công. Push code chưa chạy test là đẩy thẳng lỗi
> lên `main`, không có gì chặn lại.

## Auto-push — BẮT BUỘC

Sau **mỗi lần sửa file**, chạy ngay:

```bash
bash .claude/hooks/auto-push.sh
```

### Quy tắc
- Gọi **ngay sau khi sửa**, không chờ nhắc, không gom cuối phiên
- Script tự retry 3 lần, tự `pull --rebase` khi bị rejected
- Thoát im lặng khi tree sạch → gọi thừa vô hại, cứ gọi thoải mái

### Script báo lỗi — 2 tình huống

| Lỗi | Xử lý |
|-----|-------|
| `Remote conflict: git pull --rebase failed` | **KHÔNG** dùng `--force`. Conflict thật thì cần merge thủ công. |
| `Permission denied` | Kiểm tra quyền truy cập remote. Báo user. |

## ISSUES.md Workflow

Hermes phát hiện bug → ghi vào `ISSUES.md`. Claude Code đọc file này **đầu mỗi phiên**, thấy issue chưa có `✅ fixed` thì tự fix.

**Format mỗi issue:**
```markdown
## [YYYY-MM-DD HH:MM] Tiêu đề ngắn gọn

**File:** tên-file.py:123
**Mức độ:** critical | high | medium | low
**Mô tả:** bug gì, hậu quả thế nào
**Cách fix:** sửa cụ thể ra sao
**Đã test:** ✅ / ❌ / ⚠️ chưa test được
**Status:** (Claude Code điền) ✅ fixed in <commit>
```

**Quy tắc:**
- Issues không bao giờ bị xoá — chỉ thêm dòng `**Status:** ✅ fixed in <sha>` khi xong
- Claude Code `git add ISSUES.md` + commit cùng với file fix
- Fix xong → chạy `python test_exporter.py` + `auto-push.sh`

## SESSION_LOG.md — BẮT BUỘC cuối mỗi phiên

Trước khi kết thúc phiên, ghi một entry vào `SESSION_LOG.md` rồi commit + push.
Hermes `git pull` là đọc được, không cần ai chuyển lời qua lại.

### Quy tắc
- Entry mới đặt **lên trên cùng**, ngay dưới dòng `---` đầu tiên
- **KHÔNG** sửa hoặc xoá entry cũ — chỉ thêm
- Dùng khuôn mẫu ở cuối `SESSION_LOG.md` (trong khối comment HTML)
- Bắt buộc có: nhánh, dải commit, kết quả `test_exporter.py`, trạng thái queue,
  mục **Cần biết** (thay đổi ảnh hưởng cách chạy), mục **Còn treo** (chờ ai)

### Viết gì cho hữu ích
- Nêu rõ lỗi **hỏng âm thầm** — loại không crash, chỉ ra dữ liệu rỗng. Đây là
  thứ Hermes cần biết nhất vì rất dễ tưởng nhầm là "bài viết không có lead"
- Ghi **tác dụng phụ** của thay đổi (vd: giờ chạy GUI cũng tốn quota API)
- Đừng chép lại commit message — ghi *hệ quả* với người chạy pipeline

## Cách chạy

```bash
cd ~/GoogleGPT
source venv_mac/bin/activate

# 1 link
python app.py --headless --out ~/Desktop/leads.xlsx "https://facebook.com/..."

# Nhiều link (từ links.txt)
python app.py --headless --out ~/Desktop/leads.xlsx

# Có GUI để debug
python app.py --out ~/Desktop/leads.xlsx "https://facebook.com/..."
```

## Output Excel — 15 cột (exporter.COLUMNS)

```
Ngày tìm | Tên KH | SĐT | Nhà mạng | SĐT 2 | Nhà mạng 2 | Số lần tìm
Email | Emails | Giới tính | Ngày sinh | Location | Comment
Link bài viết | Facebook
```

## Flow chi tiết

### 1. scrape_one_post(driver, url) — app.py
- `driver.get(url)` + sleep 8-12s
- `select_newest_filter()` → chuyển sort "Mới nhất"
- Loop 10x (vòng lặp):
  - Click "Xem thêm bình luận" nếu có
  - `smart_scroll()` cuộn trang
  - `click_phone_icons_for_leads()` kích hoạt Extension
  - BS4 parse HTML → `robust_parse_comment()` từng article
  - Dừng khi đủ 5 lead hoặc hết comment

### 2. robust_parse_comment(article, url) — app.py
- Check "tác giả"/"author" → skip
- ⚠️ **SAVE `links_before` TRƯỚC khi extract nested articles** (bug đã fix)
- `nested.extract()` xoá reply
- Loop `links_before` → tìm `<a>` có text là tên + href là profile URL
- Fallback: tìm `dir='auto'` elements
- Lọc: LEAD_KEYWORDS (ib, giá, bao nhiêu, sđt...) và SELLER_KEYWORDS
- `extract_phone(comment)` → SĐT từ comment text
- Return dict với key khớp `exporter.COLUMNS` (có dấu!)

### 3. Facebook URL extraction — app.py (clean_facebook_url)
```python
m = re.match(r'^https://www\.facebook\.com/([A-Za-z0-9\.\-_]+)$', path)
```
Xử lý: `/username`, `profile.php?id=N`, `/groups/.../user/N`

⚠️ **KHÔNG dùng `patch` tool để sửa regex** — tool nhân đôi backslash.
Luôn dùng `write_file` để ghi lại toàn bộ hàm.

### 4. UID Backfill — app.py (finally block)
- `collect_uids(driver)` → lấy `uid_map` từ GraphQL interceptor
- Match bằng tên (qua `norm_name_key`) → set `_uid` + `Facebook` URL
- Giúp lead không có link FB từ BS4 vẫn có Facebook URL

### 5. FBnumber lookup — app.py + exporter.py
- `fbnumber_search_phones(uids)` → gọi `POST /v1/phone/search`
- `merge_phone_lookup(all_data, uid_map, uid_to_phone)`:
  1. Match bằng `_uid` (chính xác nhất)
  2. Match bằng normalized name
  3. Positional fallback (1-1)
- `apply_phone_info()`: ⚠️ **KHÔNG skip row có SĐT** (bug đã fix)
  - `if not _s(row.get("SĐT")): row["SĐT"] = phones[0]` — không ghi đè
  - Vẫn apply SĐT 2, nhà mạng, location, gender, birthday

### 6. Filter & export — app.py (finally) + exporter.py
```python
all_data = [r for r in all_data if r.get("SĐT", "")]  # bỏ lead không SĐT
save_excel(all_data, output_filename)                    # atomic write
```

## Pitfalls đã fix (KHÔNG lặp lại!)

| # | Vấn đề | Fix |
|---|--------|-----|
| 1 | `clean_facebook_url` trả N/A dù URL hợp lệ → 0 link FB | Dùng `write_file`, không dùng `patch` tool |
| 2 | `nested.extract()` xoá mất profile link | Save `links_before` TRƯỚC extract |
| 3 | Row có SĐT từ comment bị skip FBnumber → mất SĐT 2 | Bỏ `continue`, thêm guard `if not _s()` |
| 4 | Cột Excel trống | Key must match `exporter.COLUMNS` (có dấu: `Ngày tìm`, `Tên KH`, `SĐT`) |
| 5 | Lead không SĐT vẫn xuất hiện | Filter `[r for r in all_data if r.get("SĐT", "")]` |
| 6 | Mất dấu tiếng Việt trong XPath/regex → không khớp gì cả | Facebook render **có dấu** ("Bình luận", "2 giờ", "Vừa xong"). `TIME_PATTERN` mất dấu → `is_junk()` không lọc được timestamp; 4 selector của `open_reel_comments()` mất dấu → không mở được bình luận Reel. Luôn giữ **cả hai** biến thể có dấu và không dấu |
| 7 | FBnumber gắn vào `--headless` → chạy qua Hermes ra ~0 dòng | Bộ lọc SĐT chạy vô điều kiện, mà `run_hermes` mặc định không truyền `--headless` → không tra số → lọc xoá sạch. Đã gỡ `and args.headless`. Tra số **không liên quan** tới việc ẩn cửa sổ Chrome |
| 8 | `run_hermes.py` đọc Excel ra toàn `N/A` | Tên cột phải khớp `exporter.COLUMNS`: `Tên KH` / `Facebook` / `Ngày tìm` (không phải `Tên nick FB` / `Link FB cá nhân` / `Thời gian đăng`). Và **phải** `pd.read_excel(..., dtype=str)` — pandas ép cột SĐT thành float, `"0776791717"` → `776791717.0` |
| 9 | Fallback tên `dir='auto'` nuốt mất comment | Facebook tách 1 comment thành **nhiều** block `dir='auto'`. Lấy block đầu làm tên thì vòng bóc nội dung loại nó đi → mất từ khoá mua hàng → lead bị bỏ, hoặc `Tên KH` là mảnh comment (`"ib giá"`). Guard: block đầu không được chứa `COMMENT_MARKERS` (khớp **ranh giới từ**, không phải substring — `'ib'` không được khớp trong `"Thibault"`), **và** phần còn lại vẫn phải đủ làm lead. Lệch về phía **từ chối**: tên bị bỏ nhầm thì UID backfill vớt lại được, còn lấy nhầm mảnh comment làm tên thì vừa bẩn dữ liệu vừa phá so khớp tên ở `merge_phone_lookup` |
| 10 | `--no-fbnumber` bị `run_hermes.py` nuốt im lặng | FBnumber chạy mặc định ở **cả hai** chế độ, nên `run_hermes` phải chuyển tiếp cờ tắt xuống `app.py`. Thiếu dòng đó thì `python run_hermes.py skill_toan_nang --no-fbnumber` vẫn gọi API và tiêu quota |

## Debug checklist

Khi Excel thiếu dữ liệu, check theo thứ tự:

1. **Link FB = N/A?** → regex `clean_facebook_url` (đếm backslash), `links_before` trước extract
2. **SĐT trống?** → `extract_phone()` regex, `merge_phone_lookup` skip row
3. **SĐT 2 trống?** → `apply_phone_info` guard `if not _s()`
4. **Cột trống?** → key name khớp COLUMNS?
5. **Sai số lượng lead?** → filter SĐT empty, merge_rows dedup

## Test & debug

| File | Vai trò |
|------|---------|
| `test_exporter.py` | **Test regression 8 nhóm** — chạy sau mỗi lần sửa `app.py` / `exporter.py` / `run_hermes.py`. Không cần Selenium, không cần mạng, không cần token thật |
| `test_drive.py` | Kiểm tra kết nối Google Drive |

```bash
python test_exporter.py     # exit 0 = pass, exit 1 = có test fail
```

Mỗi nhóm test gắn với một pitfall ở bảng trên: 1→#1, 2→#2, 4→#6, 5→#3, 6→#3, 7→#4, 8→#8.

> Các file `debug_dom.py`, `debug_article.py`, `test_regex.py` từng được nhắc ở
> đây **không còn tồn tại** trong repo — đã gỡ khỏi tài liệu.
