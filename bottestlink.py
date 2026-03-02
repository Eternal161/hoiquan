from seleniumwire import webdriver 
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
from github import Github 

# ==========================================
# ⚙️ CẤU HÌNH GITHUB 
# ==========================================
GITHUB_TOKEN = "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" # Dán token bạn vừa tạo vào đây
GITHUB_REPO_NAME = "Eternal161/hoiquan" # Ví dụ: "nguyenvana/my-iptv-playlist"
GITHUB_FILE_PATH = "playlist.m3u" # Tên file khi đẩy lên GitHub
# ==========================================

options = webdriver.ChromeOptions()
options.add_argument('--headless')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

m3u_content = "#EXTM3U\n"
danh_sach_du_lieu = []
so_tran_sap_dien_ra = 0 

# BỘ LỌC CHỐNG TRÙNG LẶP: Dùng để ghi nhớ các link trận đấu đã quét
link_da_quet = set() 

try:
    wait = WebDriverWait(driver, 15)
    
    print("⏳ Đang cào dữ liệu trang chủ...")
    driver.get("https://sv2.hoiquan1.live/lich-thi-dau/bong-da")
    
    danh_sach_tran = wait.until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href*='bong-da']"))
    )

    for tran in danh_sach_tran:
        link_tran = tran.get_attribute("href")
        
        # 1. KIỂM TRA TRÙNG LẶP: Nếu link này đã quét rồi thì bỏ qua luôn!
        if link_tran in link_da_quet:
            continue
            
        toan_bo_chu = tran.text 
        teams = tran.find_elements(By.CSS_SELECTOR, "span.truncate")
        
        if len(teams) >= 2:
            team1 = teams[0].text.strip()
            team2 = teams[1].text.strip()
            
            # 2. LỌC RÁC: Nếu tên đội 1 hoặc đội 2 bị trống (chỉ có chữ "vs") thì vứt!
            if not team1 or not team2:
                continue
                
            ten_tran = f"{team1} vs {team2}"
            
            # Đánh dấu link này đã quét để lần sau không quét lại
            link_da_quet.add(link_tran)
            
            # Lấy Logo
            try:
                logos = tran.find_elements(By.CSS_SELECTOR, "img.w-12")
                logo = logos[0].get_attribute("src") if logos else ""
            except:
                logo = ""
                
            # 3. SỬA LỖI DÍNH CHỮ THỜI GIAN: Bóc tách rạch ròi Giờ và Ngày
            time_match = re.search(r"(\d{2}:\d{2})\s*[\r\n]*\s*(\d{2}/\d{2}/\d{4})", toan_bo_chu)
            if time_match:
                thoi_gian = f"{time_match.group(1)} {time_match.group(2)}" # Tự chèn 1 dấu cách ở giữa
            else:
                thoi_gian = "Giờ cập nhật sau"
            
            # Phân loại & Giới hạn 10 trận sắp diễn ra
            is_upcoming = "Sắp diễn ra" in toan_bo_chu
            
            if is_upcoming:
                if so_tran_sap_dien_ra >= 10:
                    continue 
                so_tran_sap_dien_ra += 1 

            danh_sach_du_lieu.append({
                "ten": ten_tran,
                "link": link_tran,
                "logo": logo,
                "thoi_gian": thoi_gian,
                "is_upcoming": is_upcoming
            })

    print(f"✅ Đã gom xong {len(danh_sach_du_lieu)} trận KHÔNG TRÙNG LẶP (gồm {so_tran_sap_dien_ra} trận sắp diễn ra). Bắt đầu xử lý link...\n")

    for data in danh_sach_du_lieu:
        tieu_de_dep = f"[{data['thoi_gian']}] {data['ten']}"
        print(f"👉 Xử lý: {tieu_de_dep}")
        
        if data['is_upcoming']:
            m3u_content += f'#EXTINF:-1 tvg-logo="{data["logo"]}" group-title="⏳ Sắp diễn ra", ⏰ {tieu_de_dep}\n'
            ten_khong_dau = data["ten"].replace(" ", "_").replace("/", "")
            m3u_content += f'https://cph-p2p-msl.akamaized.net/hls/live/2000341/test/master.m3u8?id={ten_khong_dau}\n'
            continue 
            
        del driver.requests 
        driver.get(data['link'])
        time.sleep(5) 
        
        link_m3u8 = None
        for request in driver.requests:
            if request.response and '.m3u8' in request.url:
                link_m3u8 = request.url
                break 
        
        if link_m3u8:
             print(f"   ✅ Đã chộp được link M3U8 gốc.")
             m3u_content += f'#EXTINF:-1 tvg-logo="{data["logo"]}" group-title="⚽ Đang đá", 🔴 {tieu_de_dep}\n'
             m3u_content += f'{link_m3u8}\n'
        else:
             print("   ❌ Lỗi: Không thấy link M3U8 ở phòng này.")

    print("\n🚀 Đang đẩy file lên GitHub...")
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(GITHUB_REPO_NAME)

    try:
        file_tren_github = repo.get_contents(GITHUB_FILE_PATH)
        repo.update_file(file_tren_github.path, "Update lọc rác", m3u_content, file_tren_github.sha)
        print("🎉 THÀNH CÔNG! Đã cập nhật file playlist.m3u lên GitHub.")
    except Exception as e: 
        if e.status == 404: 
             repo.create_file(GITHUB_FILE_PATH, "Create list", m3u_content)
             print("🎉 THÀNH CÔNG! Đã TẠO MỚI file trên GitHub.")

except Exception as e:
    print(f"❌ Có lỗi xảy ra: {e}")

finally:
    driver.quit()