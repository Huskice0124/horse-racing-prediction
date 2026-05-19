import requests
from bs4 import BeautifulSoup

# 建立年份與 Race ID 的對應表，一勞永逸解決賽程日數變動的問題
TENNO_SHO_AUTUMN_MAP = {
    2024: "202405040811",
    2025: "202505041111"
}

def get_entry_list(year_or_id=2025):
    """
    獲取出賽名單。支援傳入年份（如 2024, 2025）或完整的 12 碼 Race ID。
    """
    # 判斷傳入的是年份還是完整 ID
    if isinstance(year_or_id, int) and year_or_id in TENNO_SHO_AUTUMN_MAP:
        race_id = TENNO_SHO_AUTUMN_MAP[year_or_id]
        print(f"📅 偵測到年份 {year_or_id}，自動對應 Race ID: {race_id}")
    else:
        race_id = str(year_or_id)
        print(f"🔍 使用自定義 Race ID: {race_id}")

    url = f"https://db.netkeiba.com/race/{race_id}/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    res = requests.get(url, headers=headers)
    res.encoding = 'EUC-JP'
    soup = BeautifulSoup(res.content, "html.parser")
    
    horse_data = []
    table = soup.find("table", class_="race_table_01")
    if not table:
        print(f"❌ 找不到賽事表格，請檢查 Race ID {race_id} 是否正確。")
        return []

    rows = table.find_all("tr")[1:]
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 7: continue
        
        h_tag = cols[3].find("a")
        h_id = h_tag['href'].split('/')[-2] if h_tag else ""
        h_name = h_tag.text.strip() if h_tag else ""
        
        j_tag = cols[6].find("a")
        j_id = j_tag['href'].split('/')[-2] if j_tag else ""
        j_name = j_tag.text.strip() if j_tag else ""
        
        if h_id:
            # 統一欄位名稱，相容 get_history.py 的格式
            horse_data.append({
                "h_id": h_id, 
                "h_name": h_name, 
                "j_id": j_id, 
                "j_name": j_name
            })
                
    return horse_data

if __name__ == "__main__":
    # 測試一鍵切換 2024
    test_year = 2024
    entries = get_entry_list(test_year)
    print(f"成功測試！{test_year} 年共爬取到 {len(entries)} 匹出賽馬匹。")