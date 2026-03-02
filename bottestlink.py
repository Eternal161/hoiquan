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
options.add_argument('--headless') # GIỮ NGUYÊN ĐỂ CHẠY TRÊN GITHUB
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

m3u_content = "#EXTM3U\n"
danh_sach_du_lieu = []
so_tran_sap_dien_ra = 0 
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
        
        if link_tran in link_da_quet:
            continue
            
        toan_bo_chu = tran.text 
        teams = tran.find_elements(By.CSS_SELECTOR, "span.truncate")
        
        if len(teams) >= 2:
            team1 = teams[0].text.strip()
            team2 = teams[1].text.strip()
            
            if not team1 or not team2:
                continue
                
            ten_tran = f"{team1} vs {team2}"
            link_da_quet.add(link_tran)
            
            # 1. BẮT TÊN GIẢI ĐẤU (Lấy dòng đầu tiên của khung)
            lines = [line.strip() for line in toan_bo_chu.split('\n') if line.strip()]
            giai_dau = lines[0] if len(lines) > 0 else "Bóng Đá"
            # Lọc rác nếu dòng đầu vô tình là các chữ chung chung
            if giai_dau.lower() in ["sắp diễn ra", "bóng đá", "trực tiếp"]:
                giai_dau = lines[1] if len(lines) > 1 else "Bóng Đá"

            # 2. BẮT POSTER LÀM LOGO (Tuyệt chiêu lấy ảnh nền siêu đẹp)
            style_attr = tran.get_attribute("style")
            bg_match = re.search(r'url\("?\'?(.*?)\'?"?\)', style_attr) if style_attr else None
            
            if bg_match and "http" in bg_match.group(1):
                logo = bg_match.group(1) # Lấy link Poster gốc
            else:
                # Nếu trận nào không có poster, lấy tạm logo đội 1 để dự phòng
                try:
                    logos = tran.find_elements(By.CSS_SELECTOR, "img.w-12")
                    logo = logos[0].get_attribute("src") if logos else ""
                except:
                    logo = ""
                
            # 3. THỜI GIAN
            time_match = re.search(r"(\d{2}:\d{2})\s*[\r\n]*\s*(\d{2}/\d{2}/\d{4})", toan_bo_chu)
            if time_match:
                thoi_gian = f"{time_match.group(1)} {time_match.group(2)}"
            else:
                thoi_gian = "Giờ cập nhật sau"
            
            # 4. PHÂN LOẠI
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
                "giai_dau": giai_dau, # Thêm dữ liệu giải đấu
                "is_upcoming": is_upcoming
            })

    print(f"✅ Đã gom xong {len(danh_sach_du_lieu)} trận. Bắt đầu xử lý link...\n")

    for data in danh_sach_du_lieu:
        # CẬP NHẬT TIÊU ĐỀ: Thêm Cúp và Tên giải đấu vào giữa
        tieu_de_dep = f"[{data['thoi_gian']}] 🏆 {data['giai_dau']} | {data['ten']}"
        print(f"👉 Xử lý: {tieu_de_dep}")
        
        if data['is_upcoming']:
            m3u_content += f'#EXTINF:-1 tvg-logo="{data["logo"]}" group-title="⏳ Sắp diễn ra", ⏰ {tieu_de_dep}\n'
            m3u_content += f'http://tran-nay-chua-da-vui-long-cho.m3u8\n'
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
             m3u_content += f'#EXTINF:-1 tvg-logo="{data["logo"]}" group-title="⚽ Đang đá", 🔴 {tieu_de_dep}\n'
             m3u_content += f'{link_m3u8}\n'
        else:
             m3u_content += f'#EXTINF:-1 tvg-logo="{data["logo"]}" group-title="⚽ Lỗi link", 🔴 {tieu_de_dep}\n'
             m3u_content += f'http://loi-khong-bat-duoc-link.m3u8\n'

    print("\n🚀 Đang đẩy file lên GitHub...")
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(GITHUB_REPO_NAME)

    try:
        file_tren_github = repo.get_contents(GITHUB_FILE_PATH)
        repo.update_file(file_tren_github.path, "Update Giao dien Pro", m3u_content, file_tren_github.sha)
        print("🎉 THÀNH CÔNG! Đã cập nhật file playlist.m3u lên GitHub.")
    except Exception as e: 
        if e.status == 404: 
             repo.create_file(GITHUB_FILE_PATH, "Create list", m3u_content)
             print("🎉 THÀNH CÔNG! Đã TẠO MỚI file trên GitHub.")

except Exception as e:
    print(f"❌ Có lỗi xảy ra: {e}")

finally:
    driver.quit()

