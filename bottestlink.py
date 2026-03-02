import os
import time
import re
import json
import hashlib
import traceback
from github import Github, Auth
from seleniumwire import webdriver 
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================================
# ⚙️ CẤU HÌNH GITHUB (BẢO MẬT TOKEN)
# ==========================================
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
    "name": "Sáng",
    "color": "#1cb57a",
    "grid_number": 3,
    "image": {
        "type": "cover", 
        "url": "https://i.postimg.cc/02tKjcyN/JT3IVCOJDKW3PBRFZAZUILENLU.jpg"
    },
    "groups": [{
        "id": "live-matches",
        "name": "🔴 Trực Tiếp Bóng Đá",
        "display": "vertical",
        "grid_number": 2,
        "enable_detail": False,
        "channels": []
    }]
}

danh_sach_tran = []
link_da_quet = set()

try:
    print("🚀 Đang quét dữ liệu, tỉ số và thời gian...")
    wait = WebDriverWait(driver, 20)
    driver.get("https://sv2.hoiquan2.live/lich-thi-dau/bong-da")
    
    items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href*='bong-da']")))
    
    for item in items:
        link = item.get_attribute("href")
        if link in link_da_quet: continue
        link_da_quet.add(link)
        
        text = item.text
        
        style = item.get_attribute("style") or ""
        bg = re.search(r'url\("?\'?(.*?)\'?"?\)', style)
        poster_url = bg.group(1) if bg else "https://via.placeholder.com/1600x1200.png?text=Bong+Da"
        
        # Bơm thêm tên miền nếu link ảnh bị cụt
        if poster_url.startswith("/"):
            poster_url = "https://hoiquan1.live" + poster_url
            
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        giai_dau = lines[0].upper() if len(lines) > 0 else "BÓNG ĐÁ"
        
        teams = item.find_elements(By.CSS_SELECTOR, "span.truncate")
        if len(teams) < 2: continue
        doi_1 = teams[0].text.strip()
        doi_2 = teams[1].text.strip()
        
        time_m = re.search(r"(\d{2}:\d{2})\s*[\r\n]*\s*(\d{2}/\d{2}/\d{4})", text)
        thoi_gian = f"{time_m.group(1)} {time_m.group(2)}" if time_m else "Sắp diễn ra"
        is_live = "Sắp diễn ra" not in text
        
        # Xử lý tỉ số: xóa mọi khoảng trắng và dấu xuống dòng
        ti_so_match = re.search(r"(\d+\s*-\s*\d+)", text)
        ti_so = re.sub(r'\s+', '', ti_so_match.group(1)) if ti_so_match else ""
        
        phut_match = re.search(r"(\d{1,3}'|HT|FT|Live)", text, re.IGNORECASE)
        phut = phut_match.group(1) if phut_match else ""
        
        if is_live:
            if ti_so or phut:
                nhan_hien_thi = f"🔴 {phut} | {ti_so}".strip(" |")
            else:
                nhan_hien_thi = "🔴 Đang Đá"
        else:
            nhan_hien_thi = f"⏳ {thoi_gian}"
        
        danh_sach_tran.append({
            "link": link, "doi_1": doi_1, "doi_2": doi_2, "poster": poster_url, 
            "giai": giai_dau, "gio": thoi_gian, "is_live": is_live, "nhan": nhan_hien_thi
        })

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
            "name": f"⚽ {tran['doi_1']} vs {tran['doi_2']}",
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
            "labels": [{
                "text": tran['nhan'], 
                "position": "top-left", 
                "color": "#e50914",
                "text_color": "#ffffff"
            }],
            "sources": [{
                "id": f"src-{match_id}",
                "name": "Hội Quán",
                "contents": [{
                    "id": f"ct-{match_id}",
                    "name": f"{tran['doi_1']} vs {tran['doi_2']}",
                    "streams": [{
                        "id": f"st-{match_id}",
                        "name": "Server Chính",
                        "stream_links": [{
                            "id": f"lnk-{match_id}",
                            "name": "Vào Xem",
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

    if not GITHUB_TOKEN:
        print("❌ LỖI: Không tìm thấy Token. Hãy chạy code này thông qua GitHub Actions.")
    else:
        auth = Auth.Token(GITHUB_TOKEN)
        g = Github(auth=auth)
        repo = g.get_repo(GITHUB_REPO_NAME)
        json_content = json.dumps(du_lieu_json, ensure_ascii=False, indent=4)
        
        try:
            contents = repo.get_contents(GITHUB_FILE_PATH)
            repo.update_file(contents.path, "Bản chuẩn hóa cuối cùng", json_content, contents.sha)
            print("🎉 Cập nhật thành công file playlist.json!")
        except Exception:
            repo.create_file(GITHUB_FILE_PATH, "Tạo mới JSON", json_content)
            print("🎉 Đã tạo mới file playlist.json thành công!")

except Exception as e:
    print(f"❌ Có lỗi cực mạnh:")
    traceback.print_exc()
finally:
    driver.quit()
