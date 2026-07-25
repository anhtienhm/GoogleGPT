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
| `config.py` | Cấu hình: token FBnumber, Chrome profile path, extension path |
| `links.txt` | Danh sách URL bài viết (1 dòng/link, prefix `STT|URL`) |

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

## Debug checklist

Khi Excel thiếu dữ liệu, check theo thứ tự:

1. **Link FB = N/A?** → regex `clean_facebook_url` (đếm backslash), `links_before` trước extract
2. **SĐT trống?** → `extract_phone()` regex, `merge_phone_lookup` skip row
3. **SĐT 2 trống?** → `apply_phone_info` guard `if not _s()`
4. **Cột trống?** → key name khớp COLUMNS?
5. **Sai số lượng lead?** → filter SĐT empty, merge_rows dedup

## File debug

- `debug_dom.py` — dump HTML + UID để inspect cấu trúc Facebook
- `debug_article.py` — debug nested article structure
- `test_regex.py` — test regex pattern
