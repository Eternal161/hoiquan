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
# ⚙️ CẤU HÌNH GITHUB (Lấy từ Secrets)
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

try:
    wait = WebDriverWait(driver, 20)
    print("⏳ Đang cào dữ liệu trang chủ...")
    driver.get("https://sv2.hoiquan1.live/lich-thi-dau/bong-da")
    
    # Gom danh sách trận bóng đá
    items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href*='bong-da']")))
    
    processed_links = set()
    for item in items:
        link = item.get_attribute("href")
        if link in processed_links: continue
        processed_links.add(link)
        
        text = item.text
        # Lấy Poster/Logo
        style = item.get_attribute("style")
        bg = re.search(r'url\("?\'?(.*?)\'?"?\)', style)
        logo = bg.group(1) if bg else ""
        
        # Lấy Tên giải và Đội
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        giai = lines[0] if len(lines) > 0 else "Bóng Đá"
        teams = item.find_elements(By.CSS_SELECTOR, "span.truncate")
        ten = f"{teams[0].text} vs {teams[1].text}" if len(teams) >= 2 else "Trận đấu"
        
        # Lấy giờ (Sửa lỗi dính chữ)
        time_m = re.search(r"(\d{2}:\d{2})\s*[\r\n]*\s*(\d{2}/\d{2}/\d{4})", text)
        gio = f"{time_m.group(1)} {time_m.group(2)}" if time_m else "Sắp đá"
        
        danh_sach_tran.append({
            "link": link, "ten": ten, "logo": logo, "giai": giai, "gio": gio,
            "is_live": "Sắp diễn ra" not in text
        })

    print(f"✅ Đã gom {len(danh_sach_tran)} trận. Bắt đầu rình link...")

    for tran in danh_sach_tran:
        tieu_de = f"[{tran['gio']}] 🏆 {tran['giai']} | {tran['ten']}"
        
        if not tran['is_live']:
            m3u_content += f'#EXTINF:-1 tvg-logo="{tran["logo"]}" group-title="⏳ Sắp diễn ra", ⏰ {tieu_de}\n'
            m3u_content += f'http://tran-nay-chua-da.m3u8\n'
            continue

        print(f"🔍 Quét Server: {tran['ten']}")
        driver.get(tran['link'])
        time.sleep(10) # Chờ 10s để link m3u8 kịp sinh ra

        links_found = []
        # Lấy link từ các yêu cầu mạng (Network Requests)
        for req in driver.requests:
            if req.response and '.m3u8' in req.url and 'chunklist' not in req.url:
                if req.url not in [x[1] for x in links_found]:
                    links_found.append(("Nguồn", req.url))
        
        if not links_found:
            m3u_content += f'#EXTINF:-1 tvg-logo="{tran["logo"]}" group-title="⚽ Lỗi link", 🔴 {tieu_de}\n'
            m3u_content += f'http://loi-link-vui-long-cho.m3u8\n'
        else:
            # GỘP NHÓM: Hiện 1 dòng duy nhất, các server dự phòng nằm ngay sau
            for i, (name, url) in enumerate(links_found[:3]): # Lấy tối đa 3 nguồn tốt nhất
                suffix = "" if i == 0 else f" (Dự phòng {i})"
                m3u_content += f'#EXTINF:-1 tvg-logo="{tran["logo"]}" group-title="⚽ Đang đá", 🔴 {tieu_de}{suffix}\n'
                m3u_content += f'{url}\n'

    # ĐẨY LÊN GITHUB
    print("🚀 Đang cập nhật GitHub...")
    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(GITHUB_REPO_NAME)
    f = repo.get_contents(GITHUB_FILE_PATH)
    repo.update_file(f.path, "Auto Update Full Features", m3u_content, f.sha)
    print("🎉 THÀNH CÔNG!")

except Exception as e:
    print(f"❌ Lỗi: {e}")
finally:
    driver.quit()
