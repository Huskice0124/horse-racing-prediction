import requests
from bs4 import BeautifulSoup

def get_entry_list(race_id="202505041111"):
    # 鎖定 2025 年天皇賞(秋) 的資料庫頁面
    url = f"https://db.netkeiba.com/race/{race_id}/"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    res = requests.get(url, headers=headers)
    res.encoding = 'EUC-JP' # 日本資料庫網頁專用編碼
    soup = BeautifulSoup(res.content, "html.parser")
    
    horse_data = []
    # 抓取表格中所有的行
    table = soup.find("table", class_="race_table_01")
    if not table:
        print("找不到賽事表格，請檢查 Race ID 是否正確。")
        return []

    rows = table.find_all("tr")[1:] # 跳過標題
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 7: continue
        
        # 提取馬匹 ID 與名稱
        h_tag = cols[3].find("a")
        h_id = h_tag['href'].split('/')[-2] if h_tag else ""
        h_name = h_tag.text.strip() if h_tag else ""
        
        # 提取騎師 ID 與名稱
        j_tag = cols[6].find("a")
        j_id = j_tag['href'].split('/')[-2] if j_tag else ""
        j_name = j_tag.text.strip() if j_tag else ""
        
        if h_id:
            horse_data.append({
                "id": h_id, 
                "name": h_name, 
                "jockey_id": j_id, 
                "jockey_name": j_name
            })
                
    return horse_data