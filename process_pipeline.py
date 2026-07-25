
from pathlib import Path
import re, csv, json, datetime, os

# Cấu hình
import config  # path da nen tang (macOS / Windows / Linux)

raw_src = config.PROJECT_DIR / 'raw_comments.txt'
raw_dst = config.RAW_COMMENTS_FILE
excel_dst = config.FILTERED_EXCEL
log_dst = config.PIPELINE_LOG
filtered_journey = config.PATH_RAW_DIR / 'filtered_comments.txt'
filtered_json = config.PATH_RAW_DIR / 'filtered_comments.json'

for p in [raw_dst.parent, excel_dst.parent, filtered_journey.parent, log_dst.parent, filtered_json.parent]:
    p.mkdir(parents=True, exist_ok=True)

if not raw_src.exists():
    raise SystemExit('MISSING: ' + str(raw_src))

text = raw_src.read_text(encoding='utf-8')
raw_dst.write_text(text, encoding='utf-8')
lines = text.splitlines()

# Helper tìm link bài trước dòng STT
def find_post_link_before(lines, start_index):
    for j in range(start_index-1, -1, -1):
        line = lines[j].strip()
        if not line:
            continue
        if line.startswith('==='):
            break
        m = re.search(r'Link bài(?: gốc)?: ?(https?://\S+)', line)
        if m:
            return m.group(1).strip()
    return ''

# Parse bình luận
records = []
i = 0
while i < len(lines):
    line = lines[i].strip()
    if line.startswith('STT:'):
        stt_match = re.match(r'STT: ?(\d+)', line)
        stt = int(stt_match.group(1)) if stt_match else 0
        comment_line = lines[i+1] if i+1 < len(lines) else ''
        user_line = lines[i+2] if i+2 < len(lines) else ''
        if not comment_line.startswith('Comment:'):
            i += 1
            continue
        raw_comment = comment_line[len('Comment:'):].strip()
        user_link = ''
        if user_line.startswith('User Link:'):
            user_link = user_line[len('User Link:'):].strip()
        records.append({
            'post_link': find_post_link_before(lines, i),
            'stt': stt,
            'raw_comment': raw_comment,
            'user_link': user_link,
            'line_index': i,
        })
    i += 1

# Xoá trùng: giữ lần xuất hiện đầu tiên
seen = set(); uniques = []
for r in records:
    k = (r['post_link'], r['stt'], r['raw_comment'], r['user_link'])
    if k in seen:
        continue
    seen.add(k); uniques.append(r)
records = uniques

# Tiêu chí lọc
page_author_indicators = ['Author Đôn Tiệp Design']
author_link_probable = ['dontiepdesign']

need_signals = [
    'giá','báo giá','xin giá','bao nhiêu','chi phí','phí ','tư vấn','tư vân','xin tư vấn',
    'cần','muốn','mua','đặt','phòng','nội thất','diện tích','thi công','hoàn thiện','xây','cải tạo',
    'inbox','ib','liên hệ','sốđt','số điện thoại','zalo','call','077','038','056',
    'địa chỉ','order','nhà','wc','phòng ngủ','thiếu','chính','cho','xin','đang','có thể'
]
remove_signals = [
    'thợ ','xưởng','cung cấp','thi công cho','bạn bè','nhà thầu','nhà cung cấp','ld ','ld,','spam','quảng cáo',
    'bán nick','mua nick','link scam'
]
praise_only = [
    'mê quá','đẹp quá','xinh quá','xuất sắc','thks','thanks','cảm ơn','hay quá','ngon quá',
    'đáng yêu','đẹp','gửi thông tin','thông tin chi tiết','cám ơn','tham khảo','gửi thêm','good'
]
request_hints = [
    'xin giá','cần tư vấn','ib a','ib ở','inbox','ib e ','ib e',
    'bên a có thi công','bên có thi công','xin ảnh','xin chi phí','cho xin',
    'có làm được','chính','ib với','liên hệ'
]
happiness_signals = ['triển','đag cbi','cbi','muốn làm','đang xây','hoàn thiện','chuẩn bị','chưa','lên đời']

def classify(rec):
    c = rec['raw_comment']
    u = rec['user_link']
    lower = c.lower()
    if any(x in c for x in page_author_indicators):
        return 'remove', 'Tác giả Page'
    if any(x in u for x in author_link_probable):
        return 'remove', 'Tác giả Page'
    if any(x in lower for x in remove_signals):
        return 'remove', 'Thợ/NCC/Spam'
    signal_strict = sum(lower.count(s) for s in need_signals) + sum(int(bool(re.search(r'\b'+re.escape(s)+r'\b', lower))) for s in request_hints)
    if any(x in lower for x in happiness_signals):
        signal_strict += 2
    praise = any(x in lower for x in praise_only)
    if signal_strict >= 2 and not praise:
        return 'keep', 'Tín hiệu mạnh'
    if signal_strict >= 1 and not praise:
        return 'keep', 'Tín hiệu'
    if praise and signal_strict > 0:
        if any(x in lower for x in ['Xinh','đẹp','xinh']):
            return 'keep', 'Tín hiệu/chưa chắc'
        return 'keep', 'Tín hiệu(yếu)'
    if signal_strict == 0 and not praise:
        if lower.startswith('xin ') or 'ban a' in lower or 'loc' in lower or 'hợp' in lower:
            return 'keep', 'Tín hiệu(yếu)'
        return 'remove', 'Chỉ khen/Tag'
    return 'keep', 'Tín hiệu(yếu)'

results = []
removed = 0
kept = 0
reason_counts = {}
for rec in records:
    action, reason = classify(rec)
    rec['action'] = action
    rec['reason'] = reason
    if action == 'keep':
        results.append(rec)
        kept += 1
    else:
        removed += 1
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
results = sorted(results, key=lambda x: (x['post_link'], x['line_index']))

def extract_time(text):
    m = re.search(r'(?<!\d)(\d+[mhd])(?!\w)', text.replace(' ', ''))
    return m.group(1) if m else ''

def name_from_profile(user_link):
    if 'facebook.com/' not in user_link:
        return ''
    slug = user_link.split('facebook.com/')[-1]
    slug = slug.split('?')[0].split('/')[-1]
    slug = slug.strip('/').replace('-', ' ').replace('.', ' ').strip()
    if not slug or slug.lower() in ('', 'posts', 'profile.php', 'pages', 'groups', 'people'):
        return ''
    parts = slug.split()
    words = [w.capitalize() for w in parts]
    cleaned = [w for w in words if re.fullmatch(r'[A-Za-zÀ-ỹ]+', w)]
    return ' '.join(cleaned[:4]) if cleaned else ''

def extract_name(comment, user_link):
    name = name_from_profile(user_link)
    if len(name) >= 2:
        return name
    c = re.sub(r'\s*\d+[mhd]$', '', comment.strip())
    words = re.findall(r"[A-Za-zÀ-ỹ0-9]+", c)
    name_parts = []
    for w in words:
        fl = w[0].isupper()
        if fl and len(name_parts) < 5:
            name_parts.append(w.capitalize())
        else:
            break
    return ' '.join(name_parts) if name_parts else (words[0] if words else '')

fields = ['ten_facebook','link_facebook','noi_dung_binh_luan','thoi_gian_binh_luan','link_bai_viet','nguon']
excel_csv = str(excel_dst).replace('.xlsx', '.csv')

# CSV UTF-8 BOM cho Windows
with open(excel_csv, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    for rec in results:
        writer.writerow({
            'ten_facebook': extract_name(rec['raw_comment'], rec['user_link']),
            'link_facebook': rec['user_link'],
            'noi_dung_binh_luan': rec['raw_comment'],
            'thoi_gian_binh_luan': extract_time(rec['raw_comment']),
            'link_bai_viet': rec['post_link'],
            'nguon': 'Facebook Comment',
        })

# Xuất ra .xlsx nếu có openpyxl
out_path = excel_csv
openpyxl_error = None
try:
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = 'khach_hang_tiem_nang'
    ws.append(fields)
    for rec in results:
        ws.append([
            extract_name(rec['raw_comment'], rec['user_link']),
            rec['user_link'],
            rec['raw_comment'],
            extract_time(rec['raw_comment']),
            rec['post_link'],
            'Facebook Comment',
        ])
    wb.save(str(excel_dst))
    if excel_dst.exists():
        out_path = str(excel_dst)
except Exception as e:
    openpyxl_error = str(e).replace('\n', ' ')
    out_path = excel_csv

# filtered text + JSON
with open(filtered_json, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

with open(filtered_journey, 'a', encoding='utf-8') as f:
    f.write('= QUÉT NGÀY ' + datetime.date.today().isoformat() + ' ==\n')
    for rec in results:
        f.write('='*60 + '\n')
        f.write('Bình luận: ' + rec['raw_comment'] + '\n')
        f.write('Người dùng: ' + rec['user_link'] + '\n')
        f.write('Bài viết: ' + rec['post_link'] + '\n\n')

# Log
log_time = datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')
link_count = len(records)
raw_count = len(set(r['raw_comment'] for r in records))
err_note = ('openpyxl lỗi: ' + openpyxl_error + ';') if openpyxl_error else 'Không có lỗi scraping(lần này dùng raw_comments.txt hiện có)'
log = (
    f'[{log_time}] Đã xử lý pipeline hàng ngày:\n'
    f'- Tổng bình luận thô: {raw_count}\n'
    f'- Tổng khách hàng tiềm năng duy nhất: {kept}\n'
    f'- Đã loại: {removed} ({json.dumps(reason_counts, ensure_ascii=False)})\n'
    f'- Đầu ra: {out_path}\n'
    f'- raw_comments đã đồng bộ: {raw_dst}\n'
    f'- source: {raw_src}\n'
    f'Lỗi: {err_note}\n'
    f'------------------------\n'
)
with open(log_dst, 'a', encoding='utf-8') as f:
    f.write(log)

print(json.dumps({
    'excel_xlsx': str(excel_dst) if excel_dst.exists() else None,
    'excel_fallback': excel_csv,
    'out_path': out_path,
    'kept': len(results),
    'removed': removed,
    'removed_reasons': reason_counts,
    'raw_count': raw_count,
    'link_count': link_count,
    'raw_dst': str(raw_dst),
    'log': str(log_dst),
}, ensure_ascii=False))
