import os
import json
import hashlib
import requests
from github import Github, Auth

# ================= CẤU HÌNH CƠ BẢN =================
GITHUB_TOKEN = GITHUB_TOKEN = os.environ.get("MY_GITHUB_TOKEN")
GITHUB_REPO_NAME = "Eternal161/hoiquan" 
GITHUB_FILE_PATH = "phim.json" 
BACKGROUND_IMG = "https://imgur.com/HDRH6Ii" # DÁN LINK ẢNH NỀN VÀO ĐÂY
# ===================================================

def main():
    print("⏳ Đang lấy danh sách phim mới nhất từ API...  botphim.groovy:15 - botphim.py:15")
    
    # Lấy 2 trang đầu tiên để có lượng phim phong phú hơn (khoảng 40 phim)
    items = []
    for page in range(1, 100):
        url_list = f"https://phimapi.com/danh-sach/phim-moi-cap-nhat?page={page}"
        try:
            response = requests.get(url_list, timeout=15).json()
            items.extend(response.get('items', []))
        except Exception as e:
            print(f"❌ Lỗi khi lấy danh sách trang {page}: {e}  botphim.groovy:25 - botphim.py:25")

    # Cấu trúc JSON chuẩn cho Mon Player
    du_lieu_json = {
        "id": "hoiquan-phim-pro",
        "url": f"https://raw.githack.com/{GITHUB_REPO_NAME}/main/{GITHUB_FILE_PATH}",
        "name": "Kho Phim VIP",
        "color": "#e50914",
        "grid_number": 3,
        "image": {"type": "cover", "url": BACKGROUND_IMG},
        "groups": [] 
    }

    phim_le_channels = []
    phim_bo_channels = []

    for item in items:
        slug = item.get('slug')
        
        # Gọi API chi tiết của từng phim để lấy full metadata và danh sách tập
        url_detail = f"https://phimapi.com/phim/{slug}"
        try:
            detail_response = requests.get(url_detail, timeout=10).json()
            if not detail_response.get('status'): continue
            
            movie_data = detail_response.get('movie', {})
            ten_phim = movie_data.get('name', 'Không Tên')
            nam_sx = movie_data.get('year', '2026')
            loai_phim = movie_data.get('type', 'single') # 'single' là phim lẻ, 'series'/'hoathinh' là phim bộ
            poster_url = movie_data.get('thumb_url', BACKGROUND_IMG)
            trang_thai = movie_data.get('episode_current', 'Full') # Lấy trạng thái (VD: Tập 5/10)
            
            episodes = detail_response.get('episodes', [])
            if not episodes: continue
            
            server_data = episodes[0].get('server_data', [])
            if not server_data: continue

            match_id = "phim-" + hashlib.md5(slug.encode()).hexdigest()[:8]
            
            # --- XỬ LÝ DANH SÁCH TẬP PHIM ---
            stream_links_list = []
            for ep in server_data:
                ten_tap = ep.get('name', 'Bản Full')
                link_m3u8 = ep.get('link_m3u8', '')
                if not link_m3u8: continue
                
                ep_id = "ep-" + hashlib.md5((slug + ten_tap).encode()).hexdigest()[:6]
                stream_links_list.append({
                    "id": ep_id,
                    "name": ten_tap, # Hiển thị "Tập 1", "Tập 2" hoặc "Bản Full"
                    "type": "hls",
                    "default": True if len(stream_links_list) == 0 else False, # Để mặc định phát tập 1
                    "url": link_m3u8
                })

            if not stream_links_list: continue

            # --- ĐÓNG GÓI KÊNH ---
            kenh_json = {
                "id": match_id,
                "name": f"🎬 {ten_phim} ({nam_sx})",
                "type": "single",
                "display": "default",
                "enable_detail": False,  
                "image": {
                    "padding": 0,
                    "background_color": "#000000",
                    "display": "cover",
                    "url": poster_url, 
                    "width": 600,
                    "height": 900
                },
                # Nhãn hiển thị số tập hiện tại (Ví dụ: "🔥 Tập 5")
                "labels": [{"text": f"🔥 {trang_thai}", "position": "top-left", "color": "#e50914", "text_color": "#ffffff"}],
                "sources": [{
                    "id": f"src-{match_id}",
                    "name": "Hệ Thống Phim",
                    "contents": [{
                        "id": f"ct-{match_id}",
                        "name": ten_phim,
                        "streams": [{
                            "id": f"st-{match_id}",
                            "name": "Chọn Tập",
                            "stream_links": stream_links_list # Gắn toàn bộ danh sách tập vào đây
                        }]
                    }]
                }],
                "org_metadata": {
                    "title": ten_phim,
                    "year": nam_sx,
                    "thumb": poster_url
                }
            }

            # Phân loại vào mảng tương ứng
            if loai_phim == 'single':
                phim_le_channels.append(kenh_json)
            else:
                phim_bo_channels.append(kenh_json)
                
            print(f"✅ Đã thêm: {ten_phim}  {trang_thai} ({len(stream_links_list)} link)  botphim.groovy:126 - botphim.py:126")
            
        except Exception as e:
            print(f"⚠️ Bỏ qua phim do lỗi truy xuất API: {e}  botphim.groovy:129 - botphim.py:129")

    # --- TẠO GROUP TRÊN GIAO DIỆN ---
    if phim_le_channels:
        du_lieu_json["groups"].append({
            "id": "group-phim-le", 
            "name": "🍿 PHIM LẺ (MOVIES)", 
            "display": "vertical", 
            "grid_number": 3,
            "enable_detail": False, 
            "channels": phim_le_channels
        })
        
    if phim_bo_channels:
        du_lieu_json["groups"].append({
            "id": "group-phim-bo", 
            "name": "📺 PHIM BỘ & HOẠT HÌNH (SERIES)", 
            "display": "vertical", 
            "grid_number": 3,
            "enable_detail": False, 
            "channels": phim_bo_channels
        })

    # Đẩy lên GitHub
    if GITHUB_TOKEN:
        print("⏳ Đang tải file lên GitHub...  botphim.groovy:154 - botphim.py:154")
        auth = Auth.Token(GITHUB_TOKEN)
        g = Github(auth=auth)
        repo = g.get_repo(GITHUB_REPO_NAME)
        json_content = json.dumps(du_lieu_json, ensure_ascii=False, indent=4)
        
        try:
            contents = repo.get_contents(GITHUB_FILE_PATH)
            repo.update_file(contents.path, "Cập nhật danh sách phim tự động phân loại", json_content, contents.sha)
            print("🎉 Đã cập nhật file phim.json trên GitHub thành công!  botphim.groovy:163 - botphim.py:163")
        except Exception:
            repo.create_file(GITHUB_FILE_PATH, "Tạo kho phim đầu tiên", json_content)
            print("🎉 Đã tạo file phim.json mới trên GitHub!  botphim.groovy:166 - botphim.py:166")
    else:
        print("⚠️ Chưa có GITHUB_TOKEN, hãy thêm vào biến môi trường (Secrets) trên Github Actions.  botphim.groovy:168 - botphim.py:168")

if __name__ == "__main__":
    main()