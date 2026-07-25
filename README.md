# GoogleGPT Tool

Pipeline thu thập & phân loại bình luận Facebook để tìm khách hàng tiềm năng,
điều khiển qua Hermes Agent / Telegram.

```
links.txt ──> app.py (Selenium)  ──> .xlsx
                    │
          run_hermes.py (orchestrator)
                    │
            DeepSeek phân loại nhu cầu mua
                    │
          Excel "khách hàng tiềm năng" (Google Drive)
```

## Cấu trúc

| File | Vai trò |
|---|---|
| `config.py` | Cấu hình path đa nền tảng (macOS / Windows / Linux) — **nguồn chân lý duy nhất** |
| `app.py` | Scraper Selenium. `python app.py [url] [--out file.xlsx]` |
| `run_hermes.py` | Orchestrator, menu skill + CLI không tương tác |
| `run_clean.py` | Chạy `app.py` với `sys.path` đã loại venv của Hermes agent |
| `run_filter.py` | Lọc lead theo regex intent từ file Excel scraper |
| `process_pipeline.py` | Parse raw text → Excel/JSON/log |
| `Ten_Thu_Muc_Extension/` | Chrome extension đi kèm |

## Cài đặt

macOS: xem [README-macos.md](README-macos.md) hoặc chạy `./setup_macos.sh`

Windows / Linux:
```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # điền DEEPSEEK_API_KEY
python run_hermes.py config
```

## Chạy

```bash
python run_hermes.py                     # menu tương tác
python run_hermes.py skill_toan_nang     # chạy toàn bộ chuỗi (dùng cho agent)
```

## Lưu ý về dữ liệu

Repo này **không chứa** dữ liệu đã thu thập. `links.txt`, `raw_comments.txt`
và mọi file `.xlsx/.csv` nằm trong `.gitignore` vì chứa tên thật, link profile
và số điện thoại của người dùng Facebook — thuộc phạm vi điều chỉnh của
Nghị định 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân.

API key đặt trong `.env` (đã gitignore), không hard-code vào source.
