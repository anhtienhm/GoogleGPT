from bs4 import BeautifulSoup
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import sys
import os
import random
from datetime import datetime

import argparse
import config  # cau hinh path da nen tang

SCRIPT_DIR = str(config.PROJECT_DIR)
DEBUG_DIR = str(config.DEBUG_DIR)
config.ensure_dirs()

from exporter import COLUMNS, save_excel, merge_phone_lookup

# 1. TU KHOA NGUYEN VONG MUA HANG
LEAD_KEYWORDS = [
    'ib', 'inbox',
    'tu van', 'tư vấn',
    'bao nhieu', 'bao nhiêu', 'bn',
    'gia', 'giá', 'bao gia', 'báo giá', 'xin gia', 'xin giá', 'gia sao', 'giá sao',
    'sdt', 'sđt', 'zalo', 'dat hang', 'đặt hàng', 'mua'
]

# 2. TU KHOA BAN HANG / SPAM / CHU PAGE
SELLER_KEYWORDS = [
    'xuong e', 'xưởng e', 'xuong minh', 'xưởng mình', 'ben e', 'bên e', 'ben minh', 'bên mình',
    'chuyen thi cong', 'chuyên thi công',
    'hotline', 'dia chi', 'địa chỉ', 'lien he zalo', 'liên hệ zalo', 'lh zalo', 'lien he hotline', 'liên hệ hotline',
    'san xuat', 'sản xuất', 'cung cap', 'cung cấp', 'showroom', 'cong ty', 'công ty', 'uy tin', 'uy tín', 'inbox shop'
]

ACTION_TEXTS = {
    'thich', 'like', 'phan hoi', 'phản hồi', 'reply', 'tra loi', 'trả lời', 'chia se', 'chia sẻ', 'share',
    'tac gia', 'tác giả', 'author', 'top fan', 'xem them', 'xem thêm', 'see more', 'an', 'ẩn', 'hide',
    'bao cao', 'báo cáo', 'report', 'da chinh sua', 'đã chỉnh sửa', 'edited', 'xem ban dich', 'xem bản dịch',
    'see translation', 'viet phan hoi', 'viết phản hồi', 'write a reply', 'phu hop nhat', 'phù hợp nhất',
    'moi nhat', 'mới nhất', 'most relevant', 'newest', 'gui', 'gửi', 'send',
    'nguoi dong gop hang dau', 'người đóng góp hàng đầu', 'binh luan', 'bình luận', 'comment', 'xem them binh luan', 'xem thêm bình luận'
}

TIME_PATTERN = re.compile(
    r'^\s*(\d+\s*(giay|phut|gio|ngay|tuan|nam|[smhdwy])\s*$'
    r'|\d+\s*(Thang|thg)\s*\d+'
    r'|(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s*\d+'
    r'|Vua xong|Just now)',
    re.IGNORECASE
)

NON_PROFILE_PATHS = (
    '/posts/', '/permalink/', '/videos/', '/video/', '/photos/', '/photo',
    '/reel', '/watch', '/story.php', '/media/', '/events/', '/hashtag/',
    '/marketplace/', '/pages/', '/notes/'
)


# ============================================================
# XU LY LINK CA NHAN
# ============================================================
def clean_facebook_url(url):
    if not url or url == "N/A":
        return "N/A"

    if url.startswith('/'):
        url = 'https://www.facebook.com' + url
    url = url.replace('m.facebook.com', 'www.facebook.com').replace('web.facebook.com', 'www.facebook.com')

    m = re.search(r'profile\.php\?id=(\d+)', url)
    if m:
        return f"https://www.facebook.com/profile.php?id={m.group(1)}"

    m = re.search(r'/groups/[^/]+/user/(\d+)', url)
    if m:
        return f"https://www.facebook.com/profile.php?id={m.group(1)}"

    m = re.search(r'/people/[^/]+/(\d+)', url)
    if m:
        return f"https://www.facebook.com/profile.php?id={m.group(1)}"

    path = url.split('?')[0].rstrip('/')
    m = re.match(r'^https://www\.facebook\.com/([A-Za-z0-9\.\-_]+)$', path)
    if m and m.group(1) not in ('profile.php', 'home.php', 'photo', 'watch', 'reel'):
        return path

    return "N/A"


def is_reel(url):
    return '/reel/' in url or '/reels/' in url


def is_junk(text):
    t = text.strip().lower().rstrip(':·. ')
    if not t: return True
    if t in ACTION_TEXTS: return True
    if len(t) < 25 and TIME_PATTERN.match(t): return True
    if t.isdigit(): return True
    return False


def extract_phone(text):
    """Trich so dien thoai VN tu text"""
    cleaned = re.sub(r'(sdt|sd t|sđt|sd t|lh|call|phone|dt|zalo|so|hotline|tel)[\s:.]*', '', text.lower())
    cleaned = re.sub(r'[\s.\-()/+]', '', cleaned)
    cleaned = re.sub(r'^[^\d]+', '', cleaned)
    for p in [r'(?:84)?(?:3[2-9]|5[2689]|7[0-9]|8[1-9]|9[0-9])\d{7}', r'0\d{9}', r'\d{10,11}']:
        m = re.search(p, cleaned)
        if m:
            n = m.group(0)
            return '0' + n[2:] if n.startswith('84') and len(n) == 11 else n
    return ''


def extract_uid_from_url(url):
    """Trich UID tu Facebook profile URL."""
    if not url or url == "N/A":
        return None
    m = re.search(r'profile\.php\?id=(\d+)', url)
    if m:
        return m.group(1)
    m = re.search(r'/user/(\d+)', url)
    if m:
        return m.group(1)
    m = re.search(r'facebook\.com/(\d{10,})(?:/|$)', url)
    if m:
        return m.group(1)
    return None


def extract_time_strict(article):
    for sp in article.find_all(['span', 'a']):
        t = sp.get_text(strip=True)
        if t and len(t) < 25 and TIME_PATTERN.search(t):
            return t
    return "N/A"


# ============================================================
# BOC TACH & LOC COMMENT CHUYEN DOI
# ============================================================
def robust_parse_comment(article, target_url):
    # 1. Kiem tra nhan Tac gia / Author
    article_text_lower = article.get_text().lower()
    if 'tac gia' in article_text_lower or 'tác giả' in article_text_lower or 'author' in article_text_lower:
        return None

    author_name = "Nguoi dung Facebook"
    author_link = "N/A"

    # 2. Luu SNAPSHOT link TRUOC khi xoa nested articles
    links_before = article.find_all('a', href=True)

    # 3. Xoa reply con long ben trong
    for nested in article.find_all('div', attrs={'role': 'article'}):
        nested.extract()

    # 4. Lay thong tin Ten nick & Link FB tu snapshot da luu
    for a in links_before:
        href = a['href']
        text = a.get_text(strip=True)

        if any(x in href for x in ['/login', 'checkpoint', 'hashtag', 'music']):
            continue

        path = href.split('?')[0]
        if any(x in path for x in NON_PROFILE_PATHS):
            continue

        link = clean_facebook_url(href)
        if link != "N/A":
            if text and len(text) >= 2 and not is_junk(text) and not TIME_PATTERN.search(text):
                author_name = text
                author_link = link
                break

    # 4. Trich xuat thoi gian dang
    comment_time = extract_time_strict(article)

    # 5. Trich xuat noi dung binh luan
    content_parts = []
    for span in article.find_all(['div', 'span'], dir='auto'):
        text = " ".join(span.get_text(' ', strip=True).split())
        if not text or is_junk(text) or text == author_name or TIME_PATTERN.search(text):
            continue
        content_parts.append(text)

    content_parts = list(dict.fromkeys(content_parts))
    final = [b for b in content_parts if not any(b != o and b in o for o in content_parts)]
    comment_text = " ".join(" ".join(final).split())

    # Cat bo ten tac gia neu bi dinh o dau noi dung
    if author_name != "Nguoi dung Facebook" and comment_text.startswith(author_name):
        comment_text = comment_text[len(author_name):].strip()

    comment_lower = comment_text.lower()

    # 6. LOC CHAT CHE
    if not comment_text or comment_text == "[Anh/Sticker]" or len(comment_text) < 2:
        return None

    if any(skw in comment_lower for skw in SELLER_KEYWORDS):
        return None

    is_lead = any(lkw in comment_lower for lkw in LEAD_KEYWORDS)
    if not is_lead:
        return None

    # Du phong Regex lay link
    if author_link == "N/A":
        all_text = str(article)
        fb_link_match = re.search(r'href="(/profile\.php\?id=\d+|/[A-Za-z0-9.\-_]+)"', all_text)
        if fb_link_match:
            author_link = clean_facebook_url(fb_link_match.group(1))

    # Trich SDT tu comment
    phone_num = extract_phone(comment_text)
    uid = extract_uid_from_url(author_link) or ""

    now_str = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    return {
        "Ngày tìm": now_str,
        "Tên KH": author_name,
        "SĐT": phone_num,
        "Comment": comment_text,
        "Link bài viết": target_url,
        "Facebook": author_link,
        "_uid": uid,
        "_profile_url": author_link,
    }


# ============================================================
# MO PHONG HANH VI & CUỘN TRANG AN TOAN
# ============================================================
HEADLESS_MODE = False

def headless_sleep(min_s, max_s=None):
    if HEADLESS_MODE:
        time.sleep(1.0)
    else:
        time.sleep(random.uniform(min_s, max_s or min_s + 2))


def apply_stealth(driver):
    try:
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['vi-VN', 'vi', 'en-US', 'en']});
            """
        })
    except Exception:
        pass


def human_like_mouse_move(driver):
    if HEADLESS_MODE:
        return
    try:
        width = driver.execute_script("return window.innerWidth;") or 1280
        height = driver.execute_script("return window.innerHeight;") or 900
        target_x = random.randint(100, int(width * 0.8))
        target_y = random.randint(100, int(height * 0.8))
        actions = ActionChains(driver)
        actions.move_by_offset(target_x, target_y).perform()
        time.sleep(random.uniform(0.8, 1.5))
        actions.move_by_offset(-target_x, -target_y).perform()
    except Exception:
        pass


def smart_scroll(driver):
    scroll_amount = random.randint(300, 600)
    scroll_js = f"""
    const dialogs = document.querySelectorAll("div[role='dialog']");
    const dialog = dialogs.length > 0 ? dialogs[dialogs.length - 1] : null;

    if (dialog) {{
        const candidates = dialog.querySelectorAll('div');
        let target = null;
        for (const el of candidates) {{
            const style = window.getComputedStyle(el);
            if ((style.overflowY === 'auto' || style.overflowY === 'scroll') && el.scrollHeight > el.clientHeight + 50) {{
                target = el; break;
            }}
        }}
        if (!target) {{
            for (const el of candidates) {{
                if (el.scrollHeight > el.clientHeight + 50) {{ target = el; break; }}
            }}
        }}
        if (!target) return null;
        target.scrollTop += {scroll_amount};
        return target.scrollTop;
    }}

    window.scrollBy(0, {scroll_amount});
    const doc = document.scrollingElement || document.documentElement;
    return doc.scrollTop;
    """
    try:
        current_top = driver.execute_script(scroll_js)
        if current_top is None: return 0, True
        headless_sleep(5.0, 8.0)
        return current_top, False
    except Exception:
        return 0, True


def click_outside_popups(driver):
    try:
        js = """
        const dialogs = document.querySelectorAll("div[role='dialog']");
        if (dialogs.length > 1) {
            const popup = dialogs[dialogs.length - 1];
            const rect = popup.getBoundingClientRect();
            document.elementFromPoint(rect.x + 20, rect.y + 20).click();
        }
        """
        driver.execute_script(js)
        headless_sleep(2.0, 2.0)
    except Exception:
        pass


def click_phone_icons_for_leads(driver):
    """Chi kich hoat nut Extension cho comment thoa man tieu chuan khach mua"""
    try:
        has_dialog = bool(driver.find_elements(By.CSS_SELECTOR, "div[role='dialog']"))
        selector = "div[role='dialog'] div[role='article']" if has_dialog else "div[role='article']"
        articles = driver.find_elements(By.CSS_SELECTOR, selector)
        clicked_count = 0
        for article in articles:
            try:
                text_lower = article.text.lower()
                if 'tac gia' in text_lower or 'tác giả' in text_lower or 'author' in text_lower:
                    continue
                if any(skw in text_lower for skw in SELLER_KEYWORDS):
                    continue
                is_lead = any(lkw in text_lower for lkw in LEAD_KEYWORDS)
                if not is_lead:
                    continue
                btn_elements = article.find_elements(By.XPATH, (
                    ".//a[@href]/following-sibling::*[img or svg or @role='button' or contains(@class, 'phone')]"
                    "| .//*[contains(@class, 'scan') or contains(@class, 'phone') or contains(@class, 'ext')]"
                ))
                for elem in btn_elements:
                    if elem.is_displayed():
                        is_clicked = driver.execute_script("return arguments[0].getAttribute('data-scanned');", elem)
                        if not is_clicked:
                            driver.execute_script("arguments[0].click();", elem)
                            driver.execute_script("arguments[0].setAttribute('data-scanned', 'true');", elem)
                            clicked_count += 1
                            headless_sleep(1.0, 2.0)
            except Exception:
                continue
        if clicked_count > 0:
            print(f"   -> [AI/Filter] Da kich hoat {clicked_count} nut quet cho comment chuyen doi.")
    except Exception:
        pass


def open_reel_comments(driver):
    print("-> Phat hien REEL: dang tim nut mo bang binh luan...")
    selectors = [
        "//div[@role='button'][@aria-label='Binh luan' or @aria-label='Comment']",
        "//div[@role='button'][contains(@aria-label, 'inh luan') or contains(@aria-label, 'omment')]",
        "//span[@role='button'][contains(@aria-label, 'inh luan') or contains(@aria-label, 'omment')]",
        "//div[@aria-label='Xem binh luan' or @aria-label='View comments']",
    ]
    for sel in selectors:
        try:
            btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, sel))
            )
            driver.execute_script("arguments[0].click();", btn)
            print("-> Da click mo bang binh luan Reel.")
            headless_sleep(6.0, 6.0)
            return True
        except Exception:
            continue
    if driver.find_elements(By.CSS_SELECTOR, "div[role='article']"):
        print("-> Bang binh luan Reel co ve da mo san.")
        return True
    print("-> [CANH BAO] Khong tim thay nut mo binh luan cua Reel.")
    return False


def select_newest_filter(driver):
    try:
        print("-> Dang tim bo loc binh luan...")
        if not HEADLESS_MODE:
            human_like_mouse_move(driver)
        filter_xpath = (
            "//*[contains(text(), 'Phu hop nhat') or contains(text(), 'Phù hợp nhất') or contains(text(), 'Most relevant') "
            "or contains(text(), 'Binh luan hang dau') or contains(text(), 'Bình luận hàng đầu') or contains(text(), 'Top comments') "
            "or contains(text(), 'Tat ca binh luan') or contains(text(), 'Tất cả bình luận') or contains(text(), 'All comments')]"
        )
        filter_elem = WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.XPATH, filter_xpath))
        )
        driver.execute_script("arguments[0].click();", filter_elem)
        headless_sleep(3.0, 5.0)

        newest_xpath = "//div[@role='menuitem']//span[contains(text(), 'Moi nhat') or contains(text(), 'Mới nhất') or contains(text(), 'Newest')]"
        newest_option = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.XPATH, newest_xpath))
        )
        driver.execute_script("arguments[0].click();", newest_option)
        print("-> Da chuyen sang 'Newest'!")
        headless_sleep(4.0, 6.0)

        try:
            scan_button = WebDriverWait(driver, 4).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Scan all Comments')]"))
            )
            driver.execute_script("arguments[0].click();", scan_button)
            print("-> DA CLICK THANH CONG NUT 'Scan all Comments'!")
            time.sleep(3)
        except Exception:
            pass

    except Exception as e:
        print(f"-> Khong the chon bo loc (Co the da o che do Moi nhat). Chi tiet: {e}")


# ============================================================
# KHOI TAO TRINH DUYET
# ============================================================
def create_driver(headless=False):
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1280,900")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    if headless:
        print("Dang khoi dong Chrome AN (headless)...")
        chrome_options.add_argument("--headless=new")
    else:
        print("Dang khoi dong trinh duyet Chrome...")
        chrome_options.add_argument(f"--remote-debugging-port={config.free_port()}")

    path_to_extension = config.EXTENSION_DIR
    if path_to_extension.is_dir():
        chrome_options.add_argument(f"--load-extension={path_to_extension}")

    profile_path = config.CHROME_PROFILE_DIR
    profile_path.mkdir(parents=True, exist_ok=True)
    chrome_options.add_argument(f"--user-data-dir={profile_path}")

    chrome_binary = config.detect_chrome_binary()
    if chrome_binary:
        chrome_options.binary_location = chrome_binary

    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception:
        driver = webdriver.Chrome(service=Service(), options=chrome_options)

    if not headless:
        apply_stealth(driver)
    driver.set_page_load_timeout(60)
    return driver


def is_driver_alive(driver):
    try:
        _ = driver.current_url
        return True
    except Exception:
        return False


def is_logged_in(driver):
    try:
        driver.get("https://www.facebook.com/")
        headless_sleep(5.0, 5.0)
        if "login" in driver.current_url or "checkpoint" in driver.current_url:
            return False
        if bool(driver.find_elements(By.ID, "email")) and bool(driver.find_elements(By.ID, "pass")):
            return False
        return True
    except Exception:
        return False


def ensure_logged_in(driver, headless=False):
    if is_logged_in(driver):
        print("-> Da dang nhap Facebook tu profile da luu.")
        return True

    if headless:
        print("[CANH BAO] Chay headless nhung chua dang nhap. Thu dang nhap bang profile cu...")
        try:
            driver.get("https://www.facebook.com/")
            headless_sleep(5.0, 5.0)
        except Exception:
            pass
        if is_logged_in(driver):
            print("-> Da dang nhap sau khi load profile cu.")
            return True
        print("[LOI] Profile chua co session Facebook. Hay chay co GUI (khong --headless) de dang nhap 1 lan, sau do moi chay headless duoc.")
        return False

    print("\n" + "=" * 60)
    print("  CHUA DANG NHAP FACEBOOK.")
    print("  Cua so Chrome vua mo -> hay tu dang nhap tai khoan.")
    print("  Dang nhap xong -> quay lai day va nhan ENTER de tiep tuc.")
    print("=" * 60)

    try:
        driver.get("https://www.facebook.com/login")
    except Exception:
        pass

    input(">>> Nhan ENTER sau khi da dang nhap Facebook xong... ")
    return is_logged_in(driver)


# ============================================================
# FBNUMBER TRA SO DIEN THOAI (GraphQL interceptor)
# ============================================================
import requests as _requests

FBNUMBER_HEADERS = {
    "Authorization": f"Bearer {config.FB_NUMBER_TOKEN}",
    "Content-Type": "application/json",
}


def inject_graphql_interceptor(driver):
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": """
        window.__fb_uids__ = new Set();
        window.__fb_uid_map__ = {};
        const _oo = XMLHttpRequest.prototype.open;
        const _os = XMLHttpRequest.prototype.send;
        XMLHttpRequest.prototype.open = function(m, u) { this._url = u; return _oo.apply(this, arguments); };
        XMLHttpRequest.prototype.send = function(b) {
            this.addEventListener('load', function() {
                try {
                    const text = this.responseText;
                    if (!this._url || !text) return;
                    if (!this._url.includes('graphql') && !this._url.includes('fbapi')) return;
                    const data = JSON.parse(text);
                    const extractNames = (obj) => {
                        if (!obj || typeof obj !== 'object') return;
                        if (Array.isArray(obj)) { obj.forEach(extractNames); return; }
                        if (obj.__typename === 'User' && obj.id && obj.name && String(obj.id).length >= 10) {
                            window.__fb_uids__.add(String(obj.id));
                            window.__fb_uid_map__[String(obj.id)] = obj.name;
                        }
                        if (obj.author && obj.author.id && obj.author.name && String(obj.author.id).length >= 10) {
                            window.__fb_uids__.add(String(obj.author.id));
                            window.__fb_uid_map__[String(obj.author.id)] = obj.author.name;
                        }
                        for (const key of Object.keys(obj)) {
                            if (key === '__proto__' || key === 'constructor') continue;
                            extractNames(obj[key]);
                        }
                    };
                    extractNames(data);
                } catch(e) {}
            });
            return _os.apply(this, arguments);
        };
        const _of = window.fetch;
        if (_of) {
            window.fetch = function() {
                const url = arguments[0] || '';
                return _of.apply(this, arguments).then(function(response) {
                    if (typeof url === 'string' && (url.includes('graphql') || url.includes('fbapi'))) {
                        const clone = response.clone();
                        clone.text().then(function(text) {
                            try {
                                const data = JSON.parse(text);
                                const extract = (obj) => {
                                    if (!obj || typeof obj !== 'object') return;
                                    if (Array.isArray(obj)) { obj.forEach(extract); return; }
                                    if (obj.__typename === 'User' && obj.id && obj.name && String(obj.id).length >= 10) {
                                        window.__fb_uids__.add(String(obj.id));
                                        window.__fb_uid_map__[String(obj.id)] = obj.name;
                                    }
                                    if (obj.author && obj.author.id && obj.author.name && String(obj.author.id).length >= 10) {
                                        window.__fb_uids__.add(String(obj.author.id));
                                        window.__fb_uid_map__[String(obj.author.id)] = obj.author.name;
                                    }
                                    for (const k of Object.keys(obj)) {
                                        if (k === '__proto__' || k === 'constructor') continue;
                                        extract(obj[k]);
                                    }
                                };
                                extract(data);
                            } catch(e) {}
                        }).catch(function(){});
                    }
                    return response;
                });
            };
        }
    """})


def collect_uids(driver):
    uids = driver.execute_script("return Array.from(window.__fb_uids__ || []);")
    uid_map = driver.execute_script("return window.__fb_uid_map__ || {};")
    return uids, uid_map


def fbnumber_search_phones(uids):
    if not uids:
        return {}
    results = {}
    for idx, uid in enumerate(uids):
        try:
            r = _requests.post(
                f"{config.FB_API_URL}/phone/search",
                headers=FBNUMBER_HEADERS,
                json={"uid": uid},
                timeout=10,
            )
            if r.status_code == 201:
                data = r.json()
                if data.get("status") == "success":
                    d = data["data"]
                    results[uid] = {
                        "number": d.get("number", ""),
                        "number2": d.get("number2", ""),
                        "numberProvider": d.get("numberProvider", ""),
                        "number2Provider": d.get("number2Provider", ""),
                        "location": d.get("location", ""),
                        "gender": d.get("gender", ""),
                        "birthday": d.get("birthday", ""),
                    }
            elif r.status_code == 429:
                print(f"   [RATE LIMIT] Dung sau {idx} UIDs.")
                break
            elif r.status_code == 401:
                print(f"   [TOKEN HET HAN] Tra ve {idx} ket qua.")
                break
        except Exception as e:
            print(f"   [LOI] UID {uid}: {e}")
        if idx % 5 == 4:
            time.sleep(0.5)
        if idx % 20 == 0 and idx > 0:
            print(f"   Da xu ly {idx}/{len(uids)} UIDs, tim thay {len(results)} SDT.")
    return results


# ============================================================
# XU LY 1 BAI VIET (CUỘN DEN KHI DU 5 BINH LUAN CHUYEN DOI)
# ============================================================
def scrape_one_post(driver, target_url):
    # Chuan hoa URL: multi_permalinks -> permalink
    m = re.search(r'multi_permalinks=(\d+)', target_url)
    if m:
        group_match = re.search(r'groups/(\d+)', target_url)
        if group_match:
            target_url = f'https://www.facebook.com/groups/{group_match.group(1)}/permalink/{m.group(1)}/'
            print(f'-> Chuan hoa URL: {target_url}')

    target_url = target_url.replace("m.facebook.com", "www.facebook.com").replace("web.facebook.com", "www.facebook.com")
    comments_data = []
    seen_keys = set()

    try:
        print(f"Dang truy cap bai viet: {target_url}")
        driver.get(target_url)
        print(">>> Dang doi trang tai on dinh...")
        headless_sleep(8.0, 12.0)

        if is_reel(target_url) or '/reel/' in driver.current_url:
            open_reel_comments(driver)

        select_newest_filter(driver)

        stuck, loop_count = 0, 0

        while loop_count < 10:
            loop_count += 1
            if not is_driver_alive(driver): break

            human_like_mouse_move(driver)

            # Click nut Xem them binh luan
            try:
                btn = driver.find_element(By.XPATH, "//span[contains(text(), 'Xem them binh luan') or contains(text(), 'Xem thêm bình luận') or contains(text(), 'View more comments') or contains(text(), 'Xem them') or contains(text(), 'Xem thêm') or contains(text(), 'See more')]")
                driver.execute_script("arguments[0].click();", btn)
                headless_sleep(1.5, 1.5)
            except Exception:
                pass

            # Thuc hien cuon trang
            current_top, is_stuck = smart_scroll(driver)

            # Kich hoat nut Extension cho comment thoa man tu khoa
            click_phone_icons_for_leads(driver)

            # Trich xuat HTML
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            has_dialog = bool(driver.find_elements(By.CSS_SELECTOR, "div[role='dialog']"))

            if has_dialog:
                comment_elements = soup.select("div[role='dialog'] div[role='article'], div[role='dialog'] div[data-testid='comment'], div[role='dialog'] blockquote")
                if not comment_elements:
                    comment_elements = soup.select("div[role='article'], div[data-testid='comment'], blockquote")
            else:
                comment_elements = soup.select("div[role='article'], div[data-testid='comment'], blockquote")

            current_valid_count = 0
            temp_comments = []

            for element in comment_elements:
                row = robust_parse_comment(element, target_url)
                if row is None:
                    continue

                key = (row.get("Tên KH", ""), row["Comment"])
                if key in seen_keys:
                    continue

                temp_comments.append(row)
                seen_keys.add(key)

            comments_data.extend(temp_comments)
            current_valid_count = len(comments_data)

            print(f"Vong lap {loop_count}: Da tich luy {current_valid_count}/5 binh luan chuyen doi chuan...")

            if current_valid_count >= 5:
                print(f"   [DAT MUC TIEU] Da thu thap du {current_valid_count} binh luan chuyen doi.")
                comments_data = comments_data[:5]
                break

            if is_stuck:
                stuck += 1
                if stuck >= 3:
                    click_outside_popups(driver)
                if stuck >= 8:
                    print(f"   [KET THUC CUA SO] Bai viet da het binh luan. Tong thu duoc: {current_valid_count}")
                    break
            else:
                stuck = 0

        got_link = sum(1 for c in comments_data if c.get("Facebook", "N/A") != "N/A")
        print(f"-> Ket qua bai nay: {len(comments_data)} binh luan chuyen doi | {got_link} co link FB.")

    except Exception as e:
        print(f"Loi khi xu ly link {target_url}: {str(e)}")

    return comments_data


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=== FACEBOOK COMMENT SCRAPER (LOC KHACH MUA & BO QUA CHU PAGE/NGUOI BAN) ===")

    parser = argparse.ArgumentParser(description="Facebook comment scraper")
    parser.add_argument("url", nargs="?", default=None,
                        help="Quet 1 link duy nhat (bo trong = doc links.txt)")
    parser.add_argument("--out", default=None, help="Duong dan file .xlsx dau ra")
    parser.add_argument("--headless", action="store_true",
                        help="Chay Chrome an (khong mo cua so)")
    parser.add_argument("--no-fbnumber", action="store_true",
                        help="Khong tra cuu SDT qua FBnumber (mac dinh: co)")
    args = parser.parse_args()

    output_filename = args.out or str(config.SCRAPER_EXCEL)

    if args.url:
        urls = [args.url]
    else:
        input_file = config.LINKS_FILE
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip().startswith("http")]
        except FileNotFoundError:
            print(f"LOI: Khong tim thay file '{input_file}'.")
            sys.exit(1)

        if not urls:
            print(f"LOI: File '{input_file}' trong.")
            sys.exit(1)

    urls = list(dict.fromkeys(urls))
    globals()['HEADLESS_MODE'] = args.headless
    driver = create_driver(headless=args.headless)

    if not args.no_fbnumber and args.headless:
        inject_graphql_interceptor(driver)
        print("-> Da inject GraphQL interceptor (FBnumber).")

    if not ensure_logged_in(driver, headless=args.headless):
        print(">>> Dung chuong trinh do chua dang nhap.")
        try: driver.quit()
        except Exception: pass
        sys.exit(1)

    all_data = []

    try:
        for i, url in enumerate(urls, 1):
            print(f"\n===== [{i}/{len(urls)}] DANG XU LY BAI VIET =====")

            if not is_driver_alive(driver):
                driver = create_driver(headless=args.headless)
                ensure_logged_in(driver, headless=args.headless)

            data = scrape_one_post(driver, url)
            if data:
                all_data.extend(data)
                save_excel(all_data, output_filename)

            if i < len(urls):
                delay_between_posts = 3.0 if HEADLESS_MODE else random.uniform(12.0, 25.0)
                print(f"-> Nghi an toan {delay_between_posts:.1f} giay truoc bai tiep theo...")
                time.sleep(delay_between_posts)

    except KeyboardInterrupt:
        print("\n>>> Da dung thu cong (Ctrl+C).")
    finally:
        # Tra cuu SDT qua FBnumber
        uid_to_phone = {}
        if not args.no_fbnumber and args.headless and urls:
            print("\n===== DANG TRA CUU SO DIEN THOAI (FBnumber) =====")
            uids, uid_map = collect_uids(driver)
            print(f"-> Tim thay {len(uids)} User IDs, {len(uid_map)} co ten.")

            # Backfill Facebook URL tu uid_map bang ten
            matched_uids = 0
            if uid_map:
                from exporter import norm_name_key as _nnk
                name_to_uid = {}
                for _uid, _name in uid_map.items():
                    key = _nnk(_name)
                    if key:
                        name_to_uid.setdefault(key, _uid)
                for row in all_data:
                    if not row.get("_uid"):
                        row_key = _nnk(row.get("Tên KH", ""))
                        if row_key and row_key in name_to_uid:
                            _uid = name_to_uid[row_key]
                            row["_uid"] = _uid
                            row["Facebook"] = f"https://www.facebook.com/{_uid}"
                            row["_profile_url"] = row["Facebook"]
                            matched_uids += 1
            if matched_uids:
                print(f"-> [UID Backfill] Da match {matched_uids} lead bang ten tu GraphQL interceptor.")

            uid_to_phone = fbnumber_search_phones(uids)
            print(f"-> Tim thay {len(uid_to_phone)} so dien thoai.")
            for uid, info in uid_to_phone.items():
                phones = [info["number"], info["number2"]]
                phones = [p for p in phones if p]
                print(f"   {uid_map.get(uid, uid)}: {', '.join(phones)} ({info.get('location','')})")

            merge_phone_lookup(all_data, uid_map, uid_to_phone)

        try: driver.quit()
        except Exception: pass
        if all_data:
            # Loc bo lead khong co SDT
            before = len(all_data)
            all_data = [r for r in all_data if r.get("SĐT", "")]
            skipped = before - len(all_data)
            if skipped:
                print(f"-> Da loc bo {skipped} lead khong co SDT.")
            save_excel(all_data, output_filename)

    if all_data:
        print(f"\n>>> HOAN THANH! Da xuat {len(all_data)} binh luan chuan hoa sang file Excel.")
