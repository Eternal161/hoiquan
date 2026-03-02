import os
import time
import re
import json
import hashlib
import traceback # Thư viện mới để soi lỗi chi tiết
from github import Github, Auth
from seleniumwire import webdriver 
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================================
# ⚙️ CẤU HÌNH GITHUB (CHẠY TRÊN MÁY TÍNH)
# ==========================================
# TẠM THỜI DÁN THẲNG TOKEN CỦA BẠN VÀO ĐÂY ĐỂ TEST TRÊN VS CODE
GITHUB_TOKEN = os.environ.get("MY_GITHUB_TOKEN")
GITHUB_REPO_NAME = "Eternal161/hoiquan" 
GITHUB_FILE_PATH = "playlist.json"
# ==========================================

options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

du_lieu_json = {
    "id": "hoiquan-tv",
    "url": "https://raw.githack.com/Eternal161/hoiquan/main/playlist.json",
    "name": "Hội Quán TV",
    "color": "#1cb57a",
    "grid_number": 3,
    "image": {
        "type": "cover", 
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Soccerball.svg/500px-Soccerball.svg.png"
    },
    "groups": [
        {
            "id": "live-matches",
            "name": "🔴 Trực Tiếp Bóng Đá",
            "display": "vertical",
            "grid_number": 2,
            "enable_detail": False,
            "channels": []
        }
    ]
}

danh_sach_tran = []
link_da_quet = set()

try:
    print("🚀 Đang khởi động bot quét dữ liệu dạng JSON...")
    wait = WebDriverWait(driver, 20)
    driver.get("https://sv2.hoiquan1.live/lich-thi-dau/bong-da")
    
    # Tìm tất cả các thẻ a
    items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href*='bong-da']")))
    print(f"👀 Đã quét thấy {len(items)} thẻ chứa link bóng đá...")
    
    for item in items:
        link = item.get_attribute("href")
        if link in link_da_quet: continue
        link_da_quet.add(link)
        
        text = item.text
        
        # FIX LỖI: Lấy Poster an toàn hơn (Tránh lỗi TypeError)
        style = item.get_attribute("style") or ""
        bg = re.search(r'url\("?\'?(.*?)\'?"?\)', style)
        poster_url = bg.group(1) if bg else "https://via.placeholder.com/1600x1200.png?text=Bong+Da"
        
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        giai_dau = lines[0].upper() if len(lines) > 0 else "BÓNG ĐÁ"
        
        teams = item.find_elements(By.CSS_SELECTOR, "span.truncate")
        if len(teams) < 2: continue
        doi_1 = teams[0].text.strip()
        doi_2 = teams[1].text.strip()
        
        time_m = re.search(r"(\d{2}:\d{2})\s*[\r\n]*\s*(\d{2}/\d{2}/\d{4})", text)
        thoi_gian = f"{time_m.group(1)} {time_m.group(2)}" if time_m else "Sắp diễn ra"
        is_live = "Sắp diễn ra" not in text
        
        danh_sach_tran.append({
            "link": link, "doi_1": doi_1, "doi_2": doi_2, "poster": poster_url, 
            "giai": giai_dau, "gio": thoi_gian, "is_live": is_live
        })

    print(f"✅ Đã phân tích thành công {len(danh_sach_tran)} trận đấu. Đang lấy link m3u8...")

    for tran in danh_sach_tran:
        link_m3u8 = "http://waiting.m3u8"
        
        if tran['is_live']:
            driver.get(tran['link'])
            time.sleep(10)
            for req in driver.requests:
                if req.response and '.m3u8' in req.url and 'chunklist' not in req.url:
                    link_m3u8 = req.url
                    break
        
        match_id = "hq-" + hashlib.md5(f"{tran['doi_1']}{tran['doi_2']}".encode()).hexdigest()[:10]
        
        kenh_json = {
            "id": match_id,
            "name": f"⚽ {tran['doi_1']} vs {tran['doi_2']} | {tran['gio']}",
            "type": "single",
            "display": "default", 
            "enable_detail": True,
            "image": {
                "padding": 1,
                "background_color": "#ececec",
                "display": "contain",
                "url": tran['poster'],
                "width": 1600,
                "height": 1200
            },
            "labels": [{"text": "● Live" if tran['is_live'] else "⏳ Sắp đá", "position": "top-left", "color": "#00ffffff", "text_color": "#ff0000"}],
            "sources": [{
                "id": f"src-{match_id}",
                "name": "Hội Quán",
                "contents": [{
                    "id": f"ct-{match_id}",
                    "name": f"{tran['doi_1']} vs {tran['doi_2']}",
                    "streams": [{
                        "id": f"st-{match_id}",
                        "name": "Server 1",
                        "stream_links": [{
                            "id": f"lnk-{match_id}",
                            "name": "Link Chính",
                            "type": "hls",
                            "default": True,
                            "url": link_m3u8,
                            "request_headers": [
                                {"key": "Referer", "value": "https://hoiquan1.live/"},
                                {"key": "User-Agent", "value": "Mozilla/5.0"}
                            ]
                        }]
                    }]
                }]
            }],
            "org_metadata": {
                "league": tran['giai'],
                "team_a": tran['doi_1'],
                "team_b": tran['doi_2'],
                "logo_a": tran['poster'],
                "logo_b": tran['poster'],
                "thumb": tran['poster']
            }
        }
        
        du_lieu_json["groups"][0]["channels"].append(kenh_json)

    # ĐẨY LÊN GITHUB
    print("⏳ Đang đẩy dữ liệu lên GitHub...")
    if not GITHUB_TOKEN or GITHUB_TOKEN.startswith("ghp_xxx"):
        print("❌ LỖI: Bạn chưa điền GITHUB_TOKEN!")
    else:
        auth = Auth.Token(GITHUB_TOKEN)
        g = Github(auth=auth)
        repo = g.get_repo(GITHUB_REPO_NAME)
        json_content = json.dumps(du_lieu_json, ensure_ascii=False, indent=4)
        
        try:
            contents = repo.get_contents(GITHUB_FILE_PATH)
            repo.update_file(contents.path, "Tái sinh bot với JSON", json_content, contents.sha)
            print("🎉 Cập nhật thành công file playlist.json!")
        except Exception:
            repo.create_file(GITHUB_FILE_PATH, "Tạo mới file JSON", json_content)
            print("🎉 Đã tạo mới file playlist.json thành công!")

except Exception as e:
    print(f"❌ Có lỗi cực mạnh:")
    traceback.print_exc() # In ra đích xác lỗi ở dòng nào
finally:
    driver.quit()

