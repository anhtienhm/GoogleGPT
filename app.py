from bs4 import BeautifulSoup
import time
import re
import pandas as pd
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

import argparse
import config  # <-- cau hinh path da nen tang

SCRIPT_DIR = str(config.PROJECT_DIR)
DEBUG_DIR = str(config.DEBUG_DIR)
config.ensure_dirs()

COLUMNS = ["Link bài viết", "Tên nick FB", "Comment", "Thời gian đăng", "Link FB cá nhân"]

# 1. TỪ KHÓA NGUYỆN VỌNG MUA HÀNG (Chỉ lấy & quét các comment chứa từ khóa này)
LEAD_KEYWORDS = [
    'ib', 'inbox', 
    'tư vấn', 'tu van', 
    'bao nhiêu', 'bao nhieu', 'bn',
    'giá', 'gia', 'báo giá', 'bao gia', 'xin giá', 'xin gia', 'giá sao', 'gia sao',
    'sđt', 'sdt', 'zalo', 'đặt hàng', 'dat hang', 'mua'
]

# 2. TỪ KHÓA BÁN HÀNG / SPAM / CHỦ PAGE (Lọc bỏ các comment này)
SELLER_KEYWORDS = [
    'xưởng e', 'xưởng mình', 'bên e', 'bên mình', 'chuyên thi công', 
    'hotline', 'địa chỉ', 'liên hệ zalo', 'lh zalo', 'liên hệ hotline',
    'sản xuất', 'cung cấp', 'showroom', 'công ty', 'uy tín', 'inbox shop'
]

ACTION_TEXTS = {
    'thích', 'like', 'phản hồi', 'reply', 'trả lời', 'chia sẻ', 'share',
    'tác giả', 'author', 'top fan', 'xem thêm', 'see more', 'ẩn', 'hide',
    'báo cáo', 'report', 'đã chỉnh sửa', 'edited', 'xem bản dịch',
    'see translation', 'viết phản hồi', 'write a reply', 'phù hợp nhất',
    'mới nhất', 'most relevant', 'newest', 'gửi', 'send',
    'người đóng góp hàng đầu', 'bình luận', 'comment', 'xem thêm bình luận'
}

TIME_PATTERN = re.compile(
    r'^\s*(\d+\s*(giây|phút|giờ|ngày|tuần|năm|[smhdwy])\s*$'
    r'|\d+\s*(Tháng|thg)\s*\d+'
    r'|(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s*\d+'
    r'|Vừa xong|Just now)',
    re.IGNORECASE
)

NON_PROFILE_PATHS = (
    '/posts/', '/permalink/', '/videos/', '/video/', '/photos/', '/photo',
    '/reel', '/watch', '/story.php', '/media/', '/events/', '/hashtag/',
    '/marketplace/', '/pages/', '/notes/'
)


# ============================================================
# XỬ LÝ LINK CÁ NHÂN
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


def extract_time_strict(article):
    for sp in article.find_all(['span', 'a']):
        t = sp.get_text(strip=True)
        if t and len(t) < 25 and TIME_PATTERN.search(t):
            return t
    return "N/A"


# ============================================================
# BÓC TÁCH & LỌC COMMENT CHUYỂN ĐỔI (LOẠI BỎ CHỦ PAGE & NGUỜI BÁN)
# ============================================================
def robust_parse_comment(article, target_url):
    # 1. Kiểm tra nhãn Tác giả / Author
    article_text_lower = article.get_text().lower()
    if 'tác giả' in article_text_lower or 'author' in article_text_lower:
        return None

    # 2. Loại bỏ các comment reply con lồng bên trong
    for nested in article.find_all('div', attrs={'role': 'article'}):
        nested.extract()

    author_name = "Người dùng Facebook"
    author_link = "N/A"
    
    # 3. Lấy thông tin Tên nick & Link FB
    links = article.find_all('a', href=True)
    for a in links:
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

    # 4. Trích xuất thời gian đăng
    comment_time = extract_time_strict(article)

    # 5. Trích xuất nội dung bình luận
    content_parts = []
    for span in article.find_all(['div', 'span'], dir='auto'):
        text = " ".join(span.get_text(' ', strip=True).split())
        if not text or is_junk(text) or text == author_name or TIME_PATTERN.search(text):
            continue
        content_parts.append(text)

    content_parts = list(dict.fromkeys(content_parts))
    final = [b for b in content_parts if not any(b != o and b in o for o in content_parts)]
    comment_text = " ".join(" ".join(final).split())

    # Cắt bỏ tên tác giả nếu bị dính ở đầu nội dung
    if author_name != "Người dùng Facebook" and comment_text.startswith(author_name):
        comment_text = comment_text[len(author_name):].strip()

    comment_lower = comment_text.lower()

    # 6. LỌC CHẶT CHẼ:
    # - Bỏ qua comment rác/ảnh/sticker
    if not comment_text or comment_text == "[Ảnh/Sticker]" or len(comment_text) < 2:
        return None

    # - Bỏ qua comment của người bán / seeding chào hàng khác
    if any(skw in comment_lower for skw in SELLER_KEYWORDS):
        return None

    # - Chỉ giữ lại comment có TỪ KHÓA MUA HÀNG / CHUYỂN ĐỔI
    is_lead = any(lkw in comment_lower for lkw in LEAD_KEYWORDS)
    if not is_lead:
        return None

    # Dự phòng Regex lấy link
    if author_link == "N/A":
        all_text = str(article)
        fb_link_match = re.search(r'href="(/profile\.php\?id=\d+|/[A-Za-z0-9.\-_]+)"', all_text)
        if fb_link_match:
            author_link = clean_facebook_url(fb_link_match.group(1))

    return {
        "Link bài viết": target_url,
        "Tên nick FB": author_name,
        "Comment": comment_text,
        "Thời gian đăng": comment_time,
        "Link FB cá nhân": author_link
    }


# ============================================================
# MÔ PHỎNG HÀNH VI & CUỘN TRANG AN TOÀN
# ============================================================
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
        time.sleep(random.uniform(5.0, 8.0)) # Giãn cách an toàn giữa các lần cuộn
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
        time.sleep(2)
    except Exception:
        pass


# ============================================================
# NHẬN BIẾT & CLICK NÚT EXTENSION TRÊN COMMENT CHUYỂN ĐỔI
# ============================================================
def click_phone_icons_for_leads(driver):
    """Chỉ kích hoạt nút Extension cho comment thỏa mãn tiêu chuẩn khách mua"""
    try:
        has_dialog = bool(driver.find_elements(By.CSS_SELECTOR, "div[role='dialog']"))
        selector = "div[role='dialog'] div[role='article']" if has_dialog else "div[role='article']"
        articles = driver.find_elements(By.CSS_SELECTOR, selector)
        
        clicked_count = 0
        for article in articles:
            try:
                text_lower = article.text.lower()
                
                # Bỏ qua nếu là Tác giả/Chủ trang hoặc chứa từ khóa người bán
                if 'tác giả' in text_lower or 'author' in text_lower:
                    continue
                if any(skw in text_lower for skw in SELLER_KEYWORDS):
                    continue

                # Bắt buộc phải chứa từ khóa nhu cầu mua
                is_lead = any(lkw in text_lower for lkw in LEAD_KEYWORDS)
                if not is_lead:
                    continue

                # Tìm nút quét của Extension
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
                            time.sleep(random.uniform(1.0, 2.0))
            except Exception:
                continue

        if clicked_count > 0:
            print(f"   -> [AI/Filter] Đã kích hoạt {clicked_count} nút quét cho comment chuyển đổi.")
    except Exception:
        pass


def open_reel_comments(driver):
    print("-> Phát hiện REEL: đang tìm nút mở bảng bình luận...")
    selectors = [
        "//div[@role='button'][@aria-label='Bình luận' or @aria-label='Comment']",
        "//div[@role='button'][contains(@aria-label, 'ình luận') or contains(@aria-label, 'omment')]",
        "//span[@role='button'][contains(@aria-label, 'ình luận') or contains(@aria-label, 'omment')]",
        "//div[@aria-label='Xem bình luận' or @aria-label='View comments']",
    ]

    for sel in selectors:
        try:
            btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, sel))
            )
            driver.execute_script("arguments[0].click();", btn)
            print("-> Đã click mở bảng bình luận Reel.")
            time.sleep(6)
            return True
        except Exception:
            continue

    if driver.find_elements(By.CSS_SELECTOR, "div[role='article']"):
        print("-> Bảng bình luận Reel có vẻ đã mở sẵn.")
        return True

    print("-> [CẢNH BÁO] Không tìm thấy nút mở bình luận của Reel.")
    return False


def select_newest_filter(driver):
    try:
        print("-> Đang tìm bộ lọc bình luận...")
        human_like_mouse_move(driver)
        filter_xpath = (
            "//*[contains(text(), 'Phù hợp nhất') or contains(text(), 'Most relevant') "
            "or contains(text(), 'Bình luận hàng đầu') or contains(text(), 'Top comments') "
            "or contains(text(), 'Tất cả bình luận') or contains(text(), 'All comments')]"
        )
        
        filter_elem = WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.XPATH, filter_xpath))
        )
        driver.execute_script("arguments[0].click();", filter_elem)
        time.sleep(random.uniform(3.0, 5.0))

        newest_xpath = "//div[@role='menuitem']//span[contains(text(), 'Mới nhất') or contains(text(), 'Newest')]"
        newest_option = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.XPATH, newest_xpath))
        )
        driver.execute_script("arguments[0].click();", newest_option)
        print("-> Đã chuyển sang 'Newest'!")
        time.sleep(random.uniform(4.0, 6.0))

        try:
            scan_button = WebDriverWait(driver, 4).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Scan all Comments')]"))
            )
            driver.execute_script("arguments[0].click();", scan_button)
            print("-> ĐÃ CLICK THÀNH CÔNG NÚT 'Scan all Comments'!")
            time.sleep(3)
        except Exception:
            pass

    except Exception as e:
        print(f"-> Không thể chọn bộ lọc (Có thể đã ở chế độ Mới nhất). Chi tiết: {e}")


# ============================================================
# KHỞI TẠO TRÌNH DUYỆT
# ============================================================
def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1280,900")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument(f"--remote-debugging-port={config.free_port()}")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-software-rasterizer")
    
    path_to_extension = config.EXTENSION_DIR
    if path_to_extension.is_dir():
        chrome_options.add_argument(f"--load-extension={path_to_extension}")

    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    profile_path = config.CHROME_PROFILE_DIR
    profile_path.mkdir(parents=True, exist_ok=True)
    chrome_options.add_argument(f"--user-data-dir={profile_path}")

    chrome_binary = config.detect_chrome_binary()
    if chrome_binary:
        chrome_options.binary_location = chrome_binary

    print("Đang khởi động trình duyệt Chrome...")

    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception:
        driver = webdriver.Chrome(service=Service(), options=chrome_options)

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
        time.sleep(5)
        if "login" in driver.current_url or "checkpoint" in driver.current_url:
            return False
        if bool(driver.find_elements(By.ID, "email")) and bool(driver.find_elements(By.ID, "pass")):
            return False
        return True
    except Exception:
        return False


def ensure_logged_in(driver):
    if is_logged_in(driver):
        print("-> Đã đăng nhập Facebook từ profile đã lưu.")
        return True

    print("\n" + "=" * 60)
    print("  CHƯA ĐĂNG NHẬP FACEBOOK.")
    print("  Cửa sổ Chrome vừa mở -> hãy tự đăng nhập tài khoản.")
    print("  Đăng nhập xong -> quay lại đây và nhấn ENTER để tiếp tục.")
    print("=" * 60)

    try:
        driver.get("https://www.facebook.com/login")
    except Exception:
        pass

    input(">>> Nhấn ENTER sau khi đã đăng nhập Facebook xong... ")
    return is_logged_in(driver)


def save_excel(all_data, output_filename):
    try:
        df = pd.DataFrame(all_data)[COLUMNS]
        tmp = output_filename.replace('.xlsx', '_tmp.xlsx')
        df.to_excel(tmp, index=False, engine='openpyxl')
        os.replace(tmp, output_filename)
        print(f"[TIẾN ĐỘ] Đã lưu {len(all_data)} bình luận chuẩn hóa vào Excel.")
        return True
    except PermissionError:
        print("[CẢNH BÁO] Vui lòng đóng file Excel đang mở để lưu.")
    except Exception as e:
        print(f"[CẢNH BÁO] Lỗi ghi Excel: {str(e)}")
    return False


# ============================================================
# XỬ LÝ 1 BÀI VIẾT (CUỘN ĐẾN KHI ĐỦ 5 BÌNH LUẬN CHUYỂN ĐỔI)
# ============================================================
def scrape_one_post(driver, target_url):
    target_url = target_url.replace("m.facebook.com", "www.facebook.com").replace("web.facebook.com", "www.facebook.com")
    comments_data = []
    seen_keys = set()

    try:
        print(f"Đang truy cập bài viết: {target_url}")
        driver.get(target_url)
        print(">>> Đang đợi trang tải ổn định...")
        time.sleep(random.uniform(8.0, 12.0))

        if is_reel(target_url) or '/reel/' in driver.current_url:
            open_reel_comments(driver)

        select_newest_filter(driver)

        stuck, loop_count = 0, 0
        
        while loop_count < 10:
            loop_count += 1
            if not is_driver_alive(driver): break

            human_like_mouse_move(driver)

            # Click nút Xem thêm bình luận nếu xuất hiện
            try:
                btn = driver.find_element(By.XPATH, "//span[contains(text(), 'Xem thêm bình luận') or contains(text(), 'View more comments') or contains(text(), 'Xem thêm') or contains(text(), 'See more')]")
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(1.5)
            except Exception:
                pass

            # Thực hiện cuộn trang
            current_top, is_stuck = smart_scroll(driver)

            # Thử kích hoạt nút Extension cho các comment thỏa mãn từ khóa
            click_phone_icons_for_leads(driver)

            # Trích xuất thử HTML hiện tại để đếm số comment CHUYỂN ĐỔI CHUẨN đã thu được
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            has_dialog = bool(driver.find_elements(By.CSS_SELECTOR, "div[role='dialog']"))
            
            if has_dialog:
                comment_elements = soup.select("div[role='dialog'] div[role='article'], div[role='dialog'] div[data-testid='comment'], div[role='dialog'] blockquote")
            else:
                comment_elements = soup.select("div[role='article'], div[data-testid='comment'], blockquote")

            current_valid_count = 0
            temp_comments = []
            
            for element in comment_elements:
                row = robust_parse_comment(element, target_url)
                if row is None: 
                    continue

                key = (row["Tên nick FB"], row["Comment"])
                if key in seen_keys: 
                    continue

                temp_comments.append(row)
                seen_keys.add(key)

            comments_data.extend(temp_comments)
            current_valid_count = len(comments_data)

            print(f"Vòng lặp {loop_count}: Đã tích lũy {current_valid_count}/5 bình luận chuyển đổi chuẩn...")

            # DỪNG KHI ĐÃ THU ĐỦ 5 BÌNH LUẬN CHUYỂN ĐỔI
            if current_valid_count >= 5:
                print(f"   [ĐẠT MỤC TIÊU] Đã thu thập đủ {current_valid_count} bình luận chuyển đổi.")
                comments_data = comments_data[:5]
                break

            # Kiểm tra nếu cuộn bị kẹt (hết bình luận trên bài)
            if is_stuck:
                stuck += 1
                if stuck >= 3:
                    click_outside_popups(driver)
                if stuck >= 8:
                    print(f"   [KẾT THÚC CỬA SỔ] Bài viết đã hết bình luận. Tổng thu được: {current_valid_count}")
                    break
            else:
                stuck = 0

        got_link = sum(1 for c in comments_data if c["Link FB cá nhân"] != "N/A")
        print(f"-> Kết quả bài này: {len(comments_data)} bình luận chuyển đổi | {got_link} có link cá nhân.")

    except Exception as e:
        print(f"Lỗi khi xử lý link {target_url}: {str(e)}")

    return comments_data


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=== FACEBOOK COMMENT SCRAPER (LỌC KHÁCH MUA & BỎ QUA CHỦ PAGE/NGƯỜI BÁN) ===")

    # --- CLI contract (dung chung cho run_hermes.py) ---------------------
    #   python app.py                      -> doc toan bo links.txt
    #   python app.py <url>                -> chi quet 1 link
    #   python app.py <url> --out out.xlsx -> chi dinh file ket qua
    parser = argparse.ArgumentParser(description="Facebook comment scraper")
    parser.add_argument("url", nargs="?", default=None,
                        help="Quet 1 link duy nhat (bo trong = doc links.txt)")
    parser.add_argument("--out", default=None, help="Duong dan file .xlsx dau ra")
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
            print(f"LỖI: Không tìm thấy file '{input_file}'.")
            sys.exit(1)

        if not urls:
            print(f"LỖI: File '{input_file}' trống.")
            sys.exit(1)

    urls = list(dict.fromkeys(urls))
    driver = create_driver()

    if not ensure_logged_in(driver):
        print(">>> Dừng chương trình do chưa đăng nhập.")
        try: driver.quit()
        except Exception: pass
        sys.exit(1)

    all_data = []

    try:
        for i, url in enumerate(urls, 1):
            print(f"\n===== [{i}/{len(urls)}] ĐANG XỬ LÝ BÀI VIẾT =====")

            if not is_driver_alive(driver):
                driver = create_driver()
                ensure_logged_in(driver)

            data = scrape_one_post(driver, url)
            if data:
                all_data.extend(data)
                save_excel(all_data, output_filename)

            if i < len(urls):
                delay_between_posts = random.uniform(12.0, 25.0)
                print(f"-> Nghỉ an toàn {delay_between_posts:.1f} giây trước bài tiếp theo...")
                time.sleep(delay_between_posts)

    except KeyboardInterrupt:
        print("\n>>> Đã dừng thủ công (Ctrl+C).")
    finally:
        try: driver.quit()
        except Exception: pass
        if all_data:
            save_excel(all_data, output_filename)

    if all_data:
        print(f"\n>>> HOÀN THÀNH! Đã xuất {len(all_data)} bình luận chuẩn hóa sang file Excel.")