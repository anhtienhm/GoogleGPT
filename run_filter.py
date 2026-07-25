import pandas as pd, os, re
from datetime import datetime

import config  # path da nen tang (macOS / Windows / Linux)

OUT_XLSX = str(config.FILTERED_EXCEL)
LOG_TXT = str(config.PIPELINE_LOG)
SCRAPER_EXCEL = str(config.SCRAPER_EXCEL)
LINKS = str(config.LINKS_FILE)

config.ensure_dirs()

start_time = datetime.now()
errors = []

if os.path.exists(SCRAPER_EXCEL):
    df = pd.read_excel(SCRAPER_EXCEL)
else:
    df = pd.DataFrame()

comments_collected = len(df)

if os.path.exists(LINKS):
    with open(LINKS, 'r', encoding='utf-8') as f:
        total_links = sum(1 for line in f if line.strip().startswith('http'))
else:
    total_links = 0
    errors.append(f'Khong tim thay {LINKS}')

AUTHOR_PHRASES = ['đôn tiệp design', 'author']

def looks_like_page_or_author(name, link):
    s = ((name or '') + ' ' + (link or '')).lower()
    return any(x in s for x in ['dontiepdesign']) or any(x.lower() in name.lower() for x in AUTHOR_PHRASES)

# Strong buying/service interest
STRONG_INTENT = re.compile(
    r'\b(xin\s*(giá|báo\s*giá|chi\s*phí)|'
    r'\b(ib|ib\s*a|inbox|liên\s*hệ|liên\s*lạc)|'
    r'tư\s*vấn|'
    r'\b(cần|muốn)\b.*(tư\s*vấn|làm|xây|thi\s*công|nội\s*thất)|'
    r'\b(đang)\b.*(xây|hoàn\s*thiện|thi\s*công)|'
    r'\b(có)\b.*(chi\s*nhánh|cửa\s*hàng)|'
    r'\b(ib)\b|\b(inbox)\b|\b(liên\s*hệ)\b|'
    r'\b(mình|cần|xin)\b.*(số|địa\s*chỉ|báo\s*giá|giá))',
    re.IGNORECASE
)

PRAISE = ['đẹp quá','mê quá','chất quá','xịn quá','quá đỉnh','đỉnh cao','tuyệt vời','haha','gif','quá xịn','xịn xò']

def is_weak(text):
    low = text.lower()
    if any(t in low for t in PRAISE):
        return True
    if not STRONG_INTENT.search(text):
        return True
    return False

filtered=[]
for _,r in df.iterrows():
    name = str(r.get('Tên nick FB',''))
    text = str(r.get('Comment',''))
    link = str(r.get('Link FB cá nhân',''))
    post_link = str(r.get('Link bài viết',''))
    tm = str(r.get('Thời gian đăng',''))
    if not text or text.strip() == 'nan':
        continue
    if looks_like_page_or_author(name, link):
        continue
    if re.search(r'^(Ảnh/Sticker|GIPHY)$', text, re.IGNORECASE):
        continue
    if is_weak(text):
        continue
    filtered.append({
        'ten_facebook': name,
        'link_facebook': link,
        'noi_dung_binh_luan': text,
        'thoi_gian_binh_luan': tm,
        'link_bai_viet': post_link,
        'nguon': 'facebook'
    })

out_df = pd.DataFrame(filtered, columns=['ten_facebook','link_facebook','noi_dung_binh_luan','thoi_gian_binh_luan','link_bai_viet','nguon'])
tmp = OUT_XLSX.replace('.xlsx','_tmp.xlsx')
out_df.to_excel(tmp, index=False, engine='openpyxl')
if os.path.exists(OUT_XLSX):
    try:
        os.remove(OUT_XLSX)
    except Exception:
        pass
os.replace(tmp, OUT_XLSX)

runtime = datetime.now() - start_time
log_entry = (
    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Pipeline executed.\n"
    f" Links processed: {total_links}\n"
    f" Comments collected: {comments_collected}\n"
    f" Potential customers filtered: {len(out_df)}\n"
    f" Runtime: {runtime}\n"
    f" Errors: {len(errors)}\n"
)
if errors:
    log_entry += '\n'.join([' - '+e for e in errors]) + '\n'
log_entry += '-'*60 + '\n'

with open(LOG_TXT,'a',encoding='utf-8') as f:
    f.write(log_entry)

print('Filtered customers:', len(out_df))
print('Log written:', LOG_TXT)
print('Output:', OUT_XLSX)
