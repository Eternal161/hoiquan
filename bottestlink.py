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

GITHUB_TOKEN = os.environ.get("MY_GITHUB_TOKEN") 
GITHUB_REPO_NAME = "Eternal161/hoiquan" 
GITHUB_FILE_PATH = "playlist.json"

options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

du_lieu_json = {
    "id": "hoiquan-tv",
    "url": "https://raw.githack.com/Eternal161/hoiquan/main/playlist.json",
    "name": "Sáng TV",
    "color": "#1cb57a",
    "grid_number": 3,
    "image": {
        "type": "cover", 
        "url": "https://i.postimg.cc/02tKjcyN/JT3IVCOJDKW3PBRFZAZUILENLU.jpg"
    },
    "groups": [] 
}

danh_sach_tran = []
link_da_quet = set()

def make_absolute_url(u):
    if not u: return "https://hoiquan1.live/assets/imgs/bg-fixture-card.png"
    if u.startswith("//"): return "https:" + u
    if u.startswith("/"): return "https://hoiquan1.live" + u
    return u

def get_sort_key(t):
    if t['is_live']:
        return "0000000000"
    m = re.search(r"(\d{2}):(\d{2})\s+(\d{2})/(\d{2})/(\d{4})", t['thoi_gian_goc'])
    if m:
        return f"{m.group(5)}{m.group(4)}{m.group(3)}{m.group(1)}{m.group(2)}"
    m2 = re.search(r"(\d{2}):(\d{2})", t['thoi_gian_goc'])
    if m2:
        return f"99991231{m2.group(1)}{m2.group(2)}"
    return "9999999999"

try:
    wait = WebDriverWait(driver, 20)
    driver.get("https://sv2.hoiquan2.live/lich-thi-dau/bong-da")
    
    items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href*='bong-da']")))
    
    for item in items:
        link = item.get_attribute("href")
        if link in link_da_quet: continue
        link_da_quet.add(link)
        
        text = item.text
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        giai_dau = lines[0].upper() if len(lines) > 0 else "BÓNG ĐÁ"
        
        teams = item.find_elements(By.CSS_SELECTOR, "span.truncate")
        if len(teams) < 2: continue
        doi_1 = teams[0].text.strip()
        doi_2 = teams[1].text.strip()

        html_content = item.get_attribute("innerHTML")
        all_urls = re.findall(r'src="([^"]+)"', html_content) + re.findall(r'url\([\'"]?(.*?)[\'"]?\)', html_content)
        
        real_logos = []
        for u in all_urls:
            if "bg-fixture" not in u and "data:image" not in u:
                url_chuan = make_absolute_url(u)
                if url_chuan not in real_logos:
                    real_logos.append(url_chuan)
        
        if len(real_logos) >= 2:
            logo_1, logo_2 = real_logos[0], real_logos[1]
        elif len(real_logos) == 1:
            logo_1 = logo_2 = real_logos[0]
        else:
            logo_1 = logo_2 = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Soccerball.svg/500px-Soccerball.svg.png"

        # ĐÃ VÁ LỖI MẤT HÌNH: Trả về hình Logo Đội 1 nguyên bản để TV không bị lỗi xám ngoét
        poster_hoan_hao = logo_1

        # ĐÃ VÁ LỖI SAI LIVE: Bộ lọc nhận diện trận đấu đã kết thúc
        text_upper = text.upper()
        is_finished = "FT" in text_upper or "KT" in text_upper or "HẾT GIỜ" in text_upper
        has_score = bool(re.search(r"(\d+)\s*-\s*(\d+)", text))

        time_m = re.search(r"(\d{2}:\d{2})\s*[\r\n]*\s*(\d{2}/\d{2}/\d{4})?", text)
        if time_m:
            gio = time_m.group(1)
            ngay = time_m.group(2) if time_m.group(2) else ""
            thoi_gian_goc = f"{gio} {ngay}".strip()
        else:
            thoi_gian_goc = "Sắp diễn ra"

        # Chỉ tính là Live nếu có tỉ số/chữ Live và CHƯA kết thúc
        if (has_score and not is_finished) or (("LIVE" in text_upper or "ĐANG ĐÁ" in text_upper) and not is_finished):
            is_live = True
        else:
            is_live = False

        if is_live:
            nhan_hien_thi = f"🔴 Đang đá | {thoi_gian_goc}"
        else:
            nhan_hien_thi = f"⏳ {thoi_gian_goc}"

        danh_sach_tran.append({
            "link": link, "doi_1": doi_1, "doi_2": doi_2, 
            "poster": poster_hoan_hao, "logo_1": logo_1, "logo_2": logo_2,
            "giai": giai_dau, "is_live": is_live, "nhan": nhan_hien_thi,
            "thoi_gian_goc": thoi_gian_goc
        })

    danh_sach_tran.sort(key=get_sort_key)
    danh_sach_kenh = []

    for tran in danh_sach_tran:
        link_m3u8 = "http://waiting.m3u8"
        if tran['is_live']:
            # ĐÃ VÁ LỖI TRÙNG LINK VIDEO: Dọn dẹp sạch trí nhớ trước khi lấy trận mới
            del driver.requests
            driver.get(tran['link'])
            time.sleep(10)
            for req in driver.requests:
                if req.response and '.m3u8' in req.url and 'chunklist' not in req.url:
                    link_m3u8 = req.url
                    break
        
        match_id = "hq-" + hashlib.md5(f"{tran['doi_1']}{tran['doi_2']}".encode()).hexdigest()[:10]
        
        kenh_json = {
            "id": match_id,
            "name": f"🏆 {tran['giai']} | ⚽ {tran['doi_1']} vs {tran['doi_2']}",
            "type": "single",
            "display": "default",
            "enable_detail": False,  
            "image": {
                "padding": 1,
                "background_color": "#ffffff",
                "display": "contain",
                "url": tran['poster'], 
                "width": 1600,
                "height": 1200
            },
            "labels": [{
                "text": tran['nhan'], 
                "position": "top-left", 
                "color": "#e50914" if tran['is_live'] else "#1cb57a",
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
                "logo_a": tran['logo_1'],
                "logo_b": tran['logo_2'],
                "thumb": tran['poster']
            }
        }
        danh_sach_kenh.append(kenh_json)

    du_lieu_json["groups"].append({
        "id": "all-matches",
        "name": "🔴 Trực Tiếp Bóng Đá", 
        "display": "vertical",
        "grid_number": 3,
        "enable_detail": False,
        "channels": danh_sach_kenh
    })

    if GITHUB_TOKEN:
        auth = Auth.Token(GITHUB_TOKEN)
        g = Github(auth=auth)
        repo = g.get_repo(GITHUB_REPO_NAME)
        json_content = json.dumps(du_lieu_json, ensure_ascii=False, indent=4)
        
        try:
            contents = repo.get_contents(GITHUB_FILE_PATH)
            repo.update_file(contents.path, "Đã vá lỗi: Live, Trùng Video và Ảnh", json_content, contents.sha)
        except Exception:
            repo.create_file(GITHUB_FILE_PATH, "Đã vá lỗi: Live, Trùng Video và Ảnh", json_content)

except Exception:
    traceback.print_exc()
finally:
    driver.quit()
