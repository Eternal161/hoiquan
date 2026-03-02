import os
import time
import re
import json
import hashlib
import traceback
import urllib.parse
from github import Github, Auth
from seleniumwire import webdriver 
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================================
# ⚙️ CẤU HÌNH GITHUB (ĐÃ BẢO MẬT TOKEN)
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
    "groups": [] 
}

danh_sach_tran = []
link_da_quet = set()

def make_absolute_url(u):
    if not u: return "https://hoiquan1.live/assets/imgs/bg-fixture-card.png"
    if u.startswith("//"): return "https:" + u
    if u.startswith("/"): return "https://hoiquan1.live" + u
    return u

try:
    print("🚀 Đang quét dữ liệu, giữ nguyên Background và ẩn Tỉ số...")
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
        
        # --- LẤY BACKGROUND GỐC ---
        style = item.get_attribute("style") or ""
        bg_match = re.search(r'url\("?\'?(.*?)\'?"?\)', style)
        if bg_match:
            poster_goc = make_absolute_url(bg_match.group(1))
        else:
            poster_goc = "https://hoiquan1.live/assets/imgs/bg-fixture-card.png"

        # --- LẤY LOGO 2 ĐỘI ---
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

        # --- VẼ ẢNH: LẤY NỀN GỐC + ĐẮP LOGO + CHỮ VS ---
        svg_template = f"""<svg width="1600" height="1200" xmlns="http://www.w3.org/2000/svg">
            <image href="{poster_goc}" x="0" y="0" width="1600" height="1200" preserveAspectRatio="xMidYMid slice"/>
            <image href="{logo_1}" x="250" y="300" width="400" height="400" preserveAspectRatio="xMidYMid meet"/>
            <text x="800" y="530" font-size="140" fill="#ffffff" text-anchor="middle" font-family="sans-serif" font-weight="bold">VS</text>
            <image href="{logo_2}" x="950" y="300" width="400" height="400" preserveAspectRatio="xMidYMid meet"/>
            <text x="450" y="800" font-size="55" fill="#ffffff" text-anchor="middle" font-family="sans-serif" font-weight="bold" filter="drop-shadow(3px 3px 2px rgba(0,0,0,0.8))">{doi_1}</text>
            <text x="1150" y="800" font-size="55" fill="#ffffff" text-anchor="middle" font-family="sans-serif" font-weight="bold" filter="drop-shadow(3px 3px 2px rgba(0,0,0,0.8))">{doi_2}</text>
            <text x="800" y="1000" font-size="65" fill="#ffd700" text-anchor="middle" font-family="sans-serif" font-weight="bold" filter="drop-shadow(3px 3px 2px rgba(0,0,0,0.8))">{giai_dau}</text>
        </svg>"""
        poster_hoan_hao = "data:image/svg+xml;charset=utf-8," + urllib.parse.quote(svg_template)
        # ----------------------------------------------

        # --- XỬ LÝ NHÃN (CHỈ HIỆN THỜI GIAN/NGÀY THÁNG) ---
        time_m = re.search(r"(\d{2}:\d{2})\s*[\r\n]*\s*(\d{2}/\d{2}/\d{4})?", text)
        if time_m:
            gio = time_m.group(1)
            ngay = time_m.group(2) if time_m.group(2) else ""
            thoi_gian_goc = f"{gio} {ngay}".strip()
        else:
            thoi_gian_goc = "Sắp diễn ra"

        phut_match = re.search(r"(?i)(\d{1,3}\s*'|Phút\s*\d+|\bHT\b|\bFT\b)", text)
        phut = phut_match.group(1).strip() if phut_match else ""
        
        is_live = bool(re.search(r"(\d+)\s*-\s*(\d+)", text)) or "Live" in text or "Trực tiếp" in text

        if is_live:
            phut_hien_thi = phut if phut else "Đang đá"
            nhan_hien_thi = f"🔴 {phut_hien_thi} | {thoi_gian_goc}"
        else:
            nhan_hien_thi = f"⏳ {thoi_gian_goc}"

        danh_sach_tran.append({
            "link": link, "doi_1": doi_1, "doi_2": doi_2, 
            "poster": poster_hoan_hao, "logo_1": logo_1, "logo_2": logo_2,
            "giai": giai_dau, "is_live": is_live, "nhan": nhan_hien_thi
        })

    nhom_giai_dau = {}

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
            "enable_detail": False,  
            "image": {
                "padding": 1,
                "background_color": "#111318",
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
        
        giai = tran['giai']
        if giai not in nhom_giai_dau:
            nhom_giai_dau[giai] = []
        nhom_giai_dau[giai].append(kenh_json)

    for giai, danh_sach_kenh in nhom_giai_dau.items():
        id_nhom = "grp-" + hashlib.md5(giai.encode()).hexdigest()[:8]
        du_lieu_json["groups"].append({
            "id": id_nhom,
            "name": f"🏆 {giai}", 
            "display": "vertical",
            "grid_number": 3,
            "enable_detail": False,
            "channels": danh_sach_kenh
        })

    if not GITHUB_TOKEN:
        print("❌ LỖI: Không tìm thấy Token.")
    else:
        auth = Auth.Token(GITHUB_TOKEN)
        g = Github(auth=auth)
        repo = g.get_repo(GITHUB_REPO_NAME)
        json_content = json.dumps(du_lieu_json, ensure_ascii=False, indent=4)
        
        try:
            contents = repo.get_contents(GITHUB_FILE_PATH)
            repo.update_file(contents.path, "Hoàn thiện: Nền gốc + Ẩn Tỉ Số", json_content, contents.sha)
            print("🎉 Cập nhật thành công file playlist.json!")
        except Exception:
            repo.create_file(GITHUB_FILE_PATH, "Tạo mới JSON", json_content)
            print("🎉 Đã tạo mới file playlist.json thành công!")

except Exception as e:
    print(f"❌ Có lỗi cực mạnh:")
    traceback.print_exc()
finally:
    driver.quit()
