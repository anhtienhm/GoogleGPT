---
name: quet-data-fb
description: "Use when quét data Facebook theo nhóm. Vào group, lọc bài nhiều bình luận + comment 24h/SEO, xuất links.txt + báo cáo."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [facebook, groups, monitoring, cron, applescript, chrome, excel]
    related_skills: [facebook-keyword-collector, facebook-scraper, computer-use, xlsx]
---

# Quét Data FB (Facebook Group Watch)

Theo dõi nhóm Facebook hàng ngày (Chrome thật, đã đăng nhập):
- Mỗi nhóm: quét feed → **10 bài có nhiều bình luận**
- Mở từng bài → đếm bình luận → thu comment của bài đạt ngưỡng
- Lọc comment: **trong 24 giờ gần đây + liên quan SEO**
- Tổng hợp link bài có comment đạt lọc → **links.txt** (mặc định `~/GoogleGPT/links.txt`) → push lên repo

## Chạy

```bash
SCRIPT=~/.hermes/skills/social-media/quet-data-fb/scripts/fb-group-watch.py

# 2 group, 10 bài/nhóm, comment 24h + SEO → links.txt + báo cáo Excel
python3 "$SCRIPT" \
  --groups "https://www.facebook.com/groups/1011442304372116" \
           "https://www.facebook.com/groups/295931577185665"

# Tùy chỉnh
python3 "$SCRIPT" --groups "<url>" --max-posts 10 --hours 24 --min-comments 2
python3 "$SCRIPT" --groups "<url>" --out ~/Desktop/report.xlsx --links-out ~/Desktop/links.txt
python3 "$SCRIPT" --groups "<url>" --no-raise   # không kéo Chrome lên trước
```

### Flags

| Flag | Ý nghĩa | Mặc định |
|---|---|---|
| `--groups` | Danh sách URL group (bắt buộc) | — |
| `--max-posts` | Số bài mỗi nhóm xử lý | 10 |
| `--min-comments` | Bài phải có ≥ N bình luận mới thu comment | 2 |
| `--hours` | Lọc comment trong N giờ gần đây | 24 |
| `--feed-scrolls` | Số lần scroll feed group | 18 |
| `--out` | File báo cáo (.xlsx) | `~/Facebook/fb_group_<ts>.xlsx` |
| `--links-out` | File links.txt tổng hợp | `~/GoogleGPT/links.txt` |
| `--no-raise` | Không kéo Chrome lên trước | off |

## Lọc SEO

Comment được giữ khi: thời gian ≤ `--hours` (parse "vào N giờ/ngày trước", "vừa xong", "lúc HH:MM") **VÀ** text chứa từ khoá SEO (seo, backlink, textlink, link báo, google, từ khóa, keyword, ranking, lên top, webmaster, gmb, domain, crawl, traffic, guest post, dofollow, wordpress, index nhanh, …).

`links.txt` chỉ ghi bài có ≥1 comment đạt lọc (không ghi đè file cũ khi không có bài nào). Format: URL trần, 1 dòng/link — đúng định dạng `app.py` của GoogleGPT đọc (`startswith("http")`).

## Dữ liệu thu được

Excel (sheet "Kết quả"): STT | Nhóm | Ngày thu | Loại (post/comment) | Tác giả | Nội dung | SĐT | Thời gian | Bình luận | Reactions | URL
- SĐT cột text format, tự trích VN 10 số
- JSON cùng tên; console in TOP 10 nhiều bình luận

## Push repo + báo cáo

```bash
cd ~/GoogleGPT
git add links.txt && git commit -m "Update links.txt (group watch)" && git push origin main
source venv_mac/bin/activate   # hoặc dùng python3 hệ thống (đã có selenium/openpyxl)
python app.py --headless --out ~/Facebook/report_$(date +%F).xlsx
hermes send --to telegram:Lentop.one --file ~/Facebook/report_$(date +%F).xlsx
```

## Pitfalls (đã kiểm chứng trên máy thật)

1. **Feed card KHÔNG có số bình luận** — phải mở từng bài để đếm (aria-label `Bình luận dưới tên …` đọc ngay khi load, không cần scroll)
2. **Feed bị virtualize** — bài chỉ tồn tại trong DOM khi ở viewport → script extract DỌC ĐƯỜNG scroll (mỗi 3 lần), không extract 1 lần cuối
3. **Tab phải dùng `id`** (không dùng index — index đổi khi user đóng/mở tab). So sánh `(id of t) as text`, KHÔNG so sánh số (lỗi -10006)
4. **Phải kéo Chrome lên trước** (`set index of front window to 1` + `activate`) — nếu `document.visibilityState = hidden`, FB không render lazy content
5. **`execute javascript` chạy được trên tab nền** (nav bằng `set URL of tab id X`), nhưng lazy-load cần tab active + window visible; JS đôi khi treo → osa timeout 35s + retry 1 lần
6. **Bài chết**: "Trang này không hiển thị" → bỏ qua, không crash
7. **Đăng nhập hết hạn**: phát hiện `input[name="email"]` → báo rõ
8. Quyền: lỗi -1743 → System Settings → Privacy & Security → Automation; "not authorized" → Chrome → View → Developer → Allow JavaScript from Apple Events
9. Không chạm Chrome tay trong lúc script chạy

## Cron hàng ngày

```yaml
Schedule: 0 8 * * *
Skills: [quet-data-fb]
Prompt: >
  Chạy script quét data fb cho 2 group (URL trong skill/memory).
  Push links.txt lên repo GoogleGPT (main).
  Chạy app.py --headless để xuất báo cáo lead.
  Gửi báo cáo + tóm tắt qua Telegram: hermes send --to telegram:Lentop.one.
```

## Verification

- [ ] Chạy thử 1 group `--max-posts 3` → có bài, cột Bình luận > 0
- [ ] links.txt chỉ chứa bài có comment 24h + SEO, URL trần bắt đầu `http`
- [ ] `git pull` trên repo thấy links.txt mới
- [ ] app.py đọc links.txt ra lead Excel
- [ ] Telegram nhận được báo cáo
