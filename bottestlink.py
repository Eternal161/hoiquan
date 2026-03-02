import os
import time
import re
from github import Github, Auth
from seleniumwire import webdriver 
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================================
# ⚙️ CẤU HÌNH GITHUB
# ==========================================
GITHUB_TOKEN = os.environ.get("MY_GITHUB_TOKEN") 
GITHUB_REPO_NAME = "Eternal161/hoiquan" 
GITHUB_FILE_PATH = "playlist.m3u"
# ==========================================

options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

m3u_content = "#EXTM3U\n"
danh_sach_tran = []
link_da_quet = set()

try:
    wait = WebDriverWait(driver, 20)
    print("⏳ Đang cào dữ liệu trang chủ...")
    driver.get("https://sv2.hoiquan1.live/lich-thi-dau/bong-da")
    
    # Gom danh sách trận bóng đá
    items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href*='bong-da']")))
    
    for item in items:
        link = item.get_attribute("href")
        if link in link_da_quet: continue
        link_da_quet.add(link)
        
        text = item.text
        # Lấy Poster xịn
        style = item.get_attribute("style")
        bg = re.search(r'url\("?\'?(.*?)\'?"?\)', style)
        logo = bg.group(1) if bg else ""
        
        # Lấy Tên giải và Đội
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        giai = lines[0] if len(lines) > 0 else "Bóng Đá"
        teams = item.find_elements(By.CSS_SELECTOR, "span.truncate")
        
        if len(teams) < 2: continue
        ten = f"{teams[0].text.strip()} vs {teams[1].text.strip()}"
        
        # Lấy giờ thi đấu chuẩn
        time_m = re.search(r"(\d{2}:\d{2})\s*[\r\n]*\s*(\d{2}/\d{2}/\d{4})", text)
        gio = f"{time_m.group(1)} {time_m.group(2)}" if time_m else "Giờ cập nhật sau"
        
        is_live = "Sắp diễn ra" not in text
        
        danh_sach_tran.append({
            "link": link, "ten": ten, "logo": logo, "giai": giai, "gio": gio, "is_live": is_live
        })

    print(f"✅ Đã gom {len(danh_sach_tran)} trận. Đang bắt link server...")

    for tran in danh_sach_tran:
        tieu_de = f"[{tran['gio']}] 🏆 {tran['giai']} | {tran['ten']}"
        
        if not tran['is_live']:
            # Trận sắp đá: 1 dòng duy nhất
            m3u_content += f'#EXTINF:-1 tvg-logo="{tran["logo"]}" group-title="⏳ Sắp diễn ra", ⏰ {tieu_de}\n'
            m3u_content += f'http://cho-den-gio-da.m3u8\n'
            continue

        # TRẬN ĐANG ĐÁ: Tìm link m3u8 thật
        print(f"🔍 Đang vào phòng: {tran['ten']}")
        del driver.requests # Xóa lịch sử cũ
        driver.get(tran['link'])
        time.sleep(12) # Đợi lâu hơn để link kịp hiện

        unique_links = []
        for req in driver.requests:
            url = req.url
            if req.response and '.m3u8' in url:
                # BỘ LỌC CHỐNG LINK RÁC: Loại bỏ link phân đoạn chunklist hoặc index rác
                if any(x in url.lower() for x in ['chunklist', 'index-v1', 'variant']):
                    continue
                if url not in unique_links:
                    unique_links.append(url)
        
        if not unique_links:
            # Nếu không bắt được link, vẫn hiện tên trận để người dùng biết
            m3u_content += f'#EXTINF:-1 tvg-logo="{tran["logo"]}" group-title="⚽ Lỗi link", 🔴 {tieu_de}\n'
            m3u_content += f'http://link-dang-cap-nhat.m3u8\n'
        else:
            # CHỈ LẤY TỐI ĐA 2 SERVER TỐT NHẤT CHO GỌN
            for i, url in enumerate(unique_links[:2]):
                sv_name = "Chính" if i == 0 else f"Dự phòng {i}"
                m3u_content += f'#EXTINF:-1 tvg-logo="{tran["logo"]}" group-title="⚽ Đang đá", 🔴 {tieu_de} ({sv_name})\n'
                m3u_content += f'{url}\n'

    # ĐẨY LÊN GITHUB
    print("🚀 Đang cập nhật lên GitHub...")
    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(GITHUB_REPO_NAME)
    contents = repo.get_contents(GITHUB_FILE_PATH)
    repo.update_file(contents.path, "Fix lỗi server và lặp trận", m3u_content, contents.sha)
    print("🎉 HOÀN TẤT!")

except Exception as e:
    print(f"❌ Có lỗi: {e}")
finally:
    driver.quit()
