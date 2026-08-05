---
name: facebook-keyword-collector
description: "Use when cần thu thập thông tin Facebook theo từ khoá. Tự mở Chrome, search keyword, gom post/comment/people/groups ra Excel."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [facebook, scraping, keyword, chrome, applescript, excel]
    related_skills: [facebook-scraper, facebook-lead-gen, xlsx, computer-use]
---

# Facebook Keyword Collector

Tự động mở Chrome thật (profile đã đăng nhập Facebook) → search từ khoá trên Facebook → thu thập bài viết / bình luận / người / nhóm / fanpage → xuất Excel + JSON.

## Khi nào dùng

- Cần gom nội dung Facebook theo từ khoá (bài viết, comment, người, group, page)
- Research thị trường / theo dõi đối thủ / tìm khách hàng theo chủ đề
- Chạy lặp lại hàng ngày theo danh sách từ khoá (file)

## Yêu cầu trước khi chạy

1. Chrome đang mở + đã đăng nhập facebook.com (profile "Cá nhân 1" = Default)
2. Chrome → menu View → Developer → **Allow JavaScript from Apple Events**
3. macOS cho phép app đang chạy điều khiển Chrome (System Settings → Privacy & Security → Automation) — báo lỗi -1743 là thiếu bước này
4. `pip install openpyxl` (hoặc chạy bằng venv `~/GoogleGPT/venv_mac`)

## Chạy

```bash
SCRIPT=~/.hermes/skills/social-media/facebook-keyword-collector/scripts/fb-keyword-collector.py

# Thu bài viết theo từ khoá
python3 $SCRIPT --keywords "sàn gỗ" "thi công sàn gỗ" --scroll 8

# Thu người / nhóm / fanpage
python3 $SCRIPT --keywords "sàn gỗ" --type people --scroll 6
python3 $SCRIPT --keywords "sàn gỗ" --type groups --scroll 6
python3 $SCRIPT --keywords "sàn gỗ" --type pages --scroll 6

# Thu kèm bình luận của từng bài viết
python3 $SCRIPT --keywords "sàn gỗ" --comments --max-comment-posts 5

# Kiểm tra môi trường (Chrome + JS + đăng nhập)
python3 $SCRIPT --check
```

### Flags

| Flag | Ý nghĩa | Mặc định |
|---|---|---|
| `--keywords` | Từ khoá (nhiều từ cách space, nhớ quote) | — |
| `--keywords-file` | File từ khoá, mỗi dòng 1 từ | — |
| `--type` | `posts` / `top` / `people` / `groups` / `pages` | `posts` |
| `--scroll` | Số lần scroll trang kết quả | 8 |
| `--max-posts` | Giới hạn item mỗi từ khoá | 20 |
| `--comments` | Mở bài viết thu thêm bình luận | off |
| `--max-comment-posts` | Giới hạn bài mở để lấy comment | 5 |
| `--out` | File xuất (.xlsx) | `~/Facebook/fb_keyword_<timestamp>.xlsx` |

## Dữ liệu thu được

Excel (sheet "Kết quả"): STT | Từ khoá | Loại | Tên | Nội dung | SĐT | Thời gian | Meta | URL

- SĐT cột text format, tự trích từ nội dung/comment (SĐT VN 10 số)
- Kèm file JSON cùng tên (đầy đủ, không cắt)
- Loại: `post` (bài viết), `comment`, `people`, `groups`, `pages`
- Với post: Nội dung = text bài, Meta = lượt thích/bình luận/chia sẻ, Thời gian = aria-label link bài
- Với comment: Nội dung = bình luận, URL = link bài gốc, Meta = tên tác giả bài

## Cách hoạt động

Script mở 1 tab riêng trong Chrome front window, điều hướng từng từ khoá tới:

- `https://www.facebook.com/search/posts|people|groups|pages/?q=<kw>`
- Scroll từ từ (tránh rate limit), rồi chạy JS lấy DOM qua AppleScript `execute javascript` (pattern osa/js — xem skill `facebook-scraper`)

Trích xuất chính:

- **Bài viết**: `div[role="article"]` + text `[data-ad-preview="message"]` (fallback: span dài nhất), link bài `/posts/` hoặc `story_fbid`, link tác giả, aria-label thời gian, aria-label đếm like/comment
- **Comment**: mở từng bài, scroll + click "Xem thêm" (`div[role="button"]`), bỏ article chứa link `/posts/` (chính là bài), lấy author + text
- **People/Groups/Pages**: lọc link theo regex pattern (loại trừ link hệ thống FB), text card xung quanh

## Pitfalls

1. **Không chạm vào Chrome trong lúc script chạy** — script dùng `active tab of front window`
2. **Rate limit** — delay scroll 1.2-1.5s; nếu bị chặn (trang toàn "action required"), dừng 5-10 phút
3. **FB đổi DOM** — nếu thu 0 kết quả mà không lỗi: mở trang search, DevTools kiểm tra `div[role="article"]` còn tồn tại không, sửa selector trong script (hằng POSTS_JS / LINK_JS / COMMENTS_JS)
4. **AppleScript truncate ~4KB** — JS đã slice text ≤1500 ký tự trước khi return
5. **Login hết hạn** — script tự phát hiện (`input[name="email"]`) và báo rõ; đăng nhập lại Chrome rồi chạy
6. **Quyền** — lỗi -1743: cấp Automation; lỗi "not authorized": bật Allow JavaScript from Apple Events
7. **Từ khoá có dấu** — URL tự encode; nên thử cả bản có dấu + không dấu

## Verification

- [ ] `python3 $SCRIPT --check` → "OK — Chrome + Facebook OK"
- [ ] Chạy 1 từ khoá, scroll nhỏ → có dòng post, URL đúng dạng facebook.com
- [ ] Mở Excel: SĐT giữ số 0 đầu, filter hoạt động
- [ ] Chạy `--comments` với 1-2 bài → có dòng comment
