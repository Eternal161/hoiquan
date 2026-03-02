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
options.add_argument('--headless') # Chạy ngầm trên GitHub
options.add_argument('--no-sandbox')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

m3u_content = "#EXTM3U\n"
danh_sach_tran = []
link_da_quet = set()

try:
    wait = WebDriverWait(driver, 20)
    driver.get("https://sv2.hoiquan1.live/lich-thi-dau/bong-da")
    
    # Gom danh sách các thẻ trận đấu
    items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href*='bong-da']")))
    
    for item in items:
        link = item.get_attribute("href")
        if link in link_da_quet: continue
        link_da_quet.add(link)
        
        text = item.text
        # CHIÊU THỨ 1: LẤY POSTER (ẢNH NỀN CHỨA CẢ 2 LOGO)
        style = item.get_attribute("style")
        bg = re.search(r'url\("?\'?(.*?)\'?"?\)', style)
        poster_url = bg.group(1) if bg else ""
        
        # Bóc tách Giải đấu và Tên đội
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        giai_dau = lines[0].upper() if len(lines) > 0 else "BÓNG ĐÁ"
        
        teams = item.find_elements(By.CSS_SELECTOR, "span.truncate")
        if len(teams) < 2: continue
        doi_1 = teams[0].text.strip()
        doi_2 = teams[1].text.strip()
        
        # Bóc tách Thời gian và Ngày tháng
        time_m = re.search(r"(\d{2}:\d{2})\s*[\r\n]*\s*(\d{2}/\d{2}/\d{4})", text)
        thoi_gian = f"{time_m.group(1)} | {time_m.group(2)}" if time_m else "Sắp thi đấu"
        
        is_live = "Sắp diễn ra" not in text
        
        danh_sach_tran.append({
            "link": link, "doi_1": doi_1, "doi_2": doi_2, "poster": poster_url, 
            "giai": giai_dau, "gio": thoi_gian, "is_live": is_live
        })

    for tran in danh_sach_tran:
        # CHIÊU THỨ 2: SẮP XẾP TIÊU ĐỀ THEO HÀNG LỐI
        # Cấu trúc: [GIẢI ĐẤU] Đội 1 vs Đội 2 (Giờ)
        title_format = f"🏆 {tran['giai']} | {tran['doi_1']} vs {tran['doi_2']} | ⏰ {tran['gio']}"
        
        if not tran['is_live']:
            m3u_content += f'#EXTINF:-1 tvg-logo="{tran["poster"]}" group-title="⏳ Sắp diễn ra", {title_format}\n'
            m3u_content += f'http://waiting.m3u8\n'
        else:
            driver.get(tran['link'])
            time.sleep(12) # Đợi link m3u8 sinh ra
            
            link_m3u8 = "http://error-link.m3u8"
            for req in driver.requests:
                if req.response and '.m3u8' in req.url and 'chunklist' not in req.url:
                    link_m3u8 = req.url
                    break
            
            group = "⚽ Đang đá" if link_m3u8 != "http://error-link.m3u8" else "❌ Lỗi link"
            m3u_content += f'#EXTINF:-1 tvg-logo="{tran["poster"]}" group-title="{group}", 🔴 {title_format}\n'
            m3u_content += f'{link_m3u8}\n'

    # Đẩy lên GitHub (Sử dụng cách thức đã fix lỗi thụt lề trước đó)
    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(GITHUB_REPO_NAME)
    contents = repo.get_contents(GITHUB_FILE_PATH)
    repo.update_file(contents.path, "Giao diện Poster Pro", m3u_content, contents.sha)
    print("🎉 Cập nhật giao diện thành công!")

except Exception as e:
    print(f"❌ Có lỗi: {e}")
finally:
    driver.quit()
