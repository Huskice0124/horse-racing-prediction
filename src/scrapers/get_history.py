import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import os
import random

# --- 1. 基礎代碼映射 ---
WEATHER_MAP = {"晴": 1, "曇": 2, "小雨": 3, "雨": 4, "雪": 5}
TRACK_MAP = {"良": 1, "稍重": 2, "重": 3, "不良": 4}

def parse_weight(weight_str):
    """拆解馬體重字串，例如 '470(+4)' -> 470, 4"""
    try:
        match = re.match(r"(\d+)\(([\+\-]?\d+)\)", str(weight_str))
        if match:
            return int(match.group(1)), int(match.group(2))
        return int(weight_str), 0
    except:
        return None, None

def parse_finish_time(time_str):
    """將完賽時間字串 '1:57.5' 轉換為總秒數 117.5"""
    try:
        if not time_str or ":" not in time_str:
            return None
        minutes, seconds = time_str.split(':')
        return int(minutes) * 60 + float(seconds)
    except:
        return None

# --- 2. 核心功能：抓取出賽名單 ---
def get_entry_list(race_id):
    url = f"https://db.netkeiba.com/race/{race_id}/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'EUC-JP'
        soup = BeautifulSoup(res.content, "html.parser")
        table = soup.find("table", class_="race_table_01")
        if not table: return []
        
        entries = []
        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) < 7: continue
            h_link = cols[3].find("a")
            j_link = cols[6].find("a")
            if h_link and j_link:
                entries.append({
                    "h_id": h_link['href'].split('/')[-2],
                    "h_name": h_link.text.strip(),
                    "j_id": j_link['href'].split('/')[-2],
                    "j_name": j_link.text.strip()
                })
        return entries
    except Exception as e:
        print(f"名單抓取錯誤: {e}")
        return []
import re

# --- 安全抓取輔助函式 ---
def safe_get(cols, index):
    """防止因為特殊賽事導致欄位減少，出現 Index Error"""
    try:
        if index < len(cols):
            return cols[index].text.strip()
        return ""
    except:
        return ""

# --- 3. 核心功能：抓取馬匹戰績 (智慧掃描防跑位版) ---
def scrape_horse_history(h_id, h_name):
    url = f"https://db.netkeiba.com/horse/result/{h_id}/"
    try:
        time.sleep(random.uniform(2, 3))
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        soup = BeautifulSoup(res.content, "html.parser", from_encoding="euc-jp")
        table = soup.find("table", class_="nk_tb_common")
        if not table: return None

        records = []
        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            
            # 確保是正規賽事紀錄 (排除取消賽事或標題列)
            if len(cols) < 15: continue

            row_data = {
                "horse_id": h_id,
                "horse_name": h_name,
                "日付": safe_get(cols, 0),
                "開催": safe_get(cols, 1),
                "天気": safe_get(cols, 2),
                "R": safe_get(cols, 3),
                "レース名": safe_get(cols, 4),
                "頭数": "", "枠番": "", "馬番": "", "オッズ": "", "人気": "", "着順": "",
                "騎手ID": "", "騎手": "", "斤量": "", "距離": "", "馬場": "", "タイム": "",
                "着差": "", "通過": "", "ペース": "", "上り": "", "馬体重": ""
            }

            # --- 1. 處理左側固定數據 ---
            # 判斷 index 5 是否為頭數(純數字)。如果不是，代表有「映像」圖示卡在中間，數字要從 6 開始算
            idx = 5
            if len(cols) > 5 and not cols[5].text.strip().isdigit():
                idx = 6
            
            row_data["頭数"] = safe_get(cols, idx)
            row_data["枠番"] = safe_get(cols, idx+1)
            row_data["馬番"] = safe_get(cols, idx+2)
            row_data["オッズ"] = safe_get(cols, idx+3)
            row_data["人気"] = safe_get(cols, idx+4)
            row_data["着順"] = safe_get(cols, idx+5)
            row_data["斤量"] = safe_get(cols, idx+7)

            # 抓取騎手 ID 與姓名
            jockey_col = cols[idx+6] if (idx+6) < len(cols) else None
            if jockey_col:
                j_tag = jockey_col.find("a")
                row_data["騎手ID"] = j_tag['href'].split('/')[-2] if j_tag else ""
                row_data["騎手"] = jockey_col.text.strip()

            # --- 2. 處理右側浮動數據 (用特徵掃描，徹底無視欄位位移與 **) ---
            time_idx = -1
            for i, col in enumerate(cols):
                txt = col.text.strip()
                if not txt or txt == "**": continue

                if re.match(r"^[芝ダ障].*\d{4}$", txt):
                    row_data["距離"] = txt
                elif txt in ["良", "稍重", "重", "不良", "稍", "不"]:
                    row_data["馬場"] = txt
                elif re.match(r"^\d+:\d{2}\.\d$", txt):
                    row_data["タイム"] = txt
                    time_idx = i  # 記住完賽時間的位子，著差就在它隔壁
                elif re.match(r"^\d{2}\.\d$", txt):
                    row_data["上り"] = txt
                elif re.match(r"^\d{3}(\([+-]?\d*\))?$", txt):
                    row_data["馬体重"] = txt
                elif re.match(r"^\d{2}\.\d-\d{2}\.\d$", txt):
                    row_data["ペース"] = txt
                elif re.match(r"^\d+(-\d+)+$", txt) and "." not in txt:
                    row_data["通過"] = txt

            # --- 3. 處理著差 (永遠跟在完賽時間後面) ---
            if time_idx != -1:
                row_data["着差"] = safe_get(cols, time_idx + 1)

            records.append(row_data)

        return records
    except Exception as e: 
        print(f"戰績抓取錯誤 ({h_name}): {e}")
        return None
# --- 4. 主程式執行 ---
if __name__ == "__main__":
    RACE_ID = "202505041111" # 2025 天皇賞(秋)
    print(f"🚀 開始攻堅 Race ID: {RACE_ID}")
    
    entries = get_entry_list(RACE_ID)
    if not entries:
        print("❌ 無法獲取出賽名單，請檢查 Race ID 或網路。")
    else:
        print(f"✅ 成功獲取 {len(entries)} 匹馬名單。")
        final_list = []
        for h in entries:
            print(f"正在挖掘: {h['h_name']}...")
            history = scrape_horse_history(h['h_id'], h['h_name'])
            
            # --- 重大修正：不再覆蓋騎師名稱，直接合併歷史紀錄 ---
            if history:
                final_list.extend(history)
        
        # 儲存資料
        if final_list:
            df = pd.DataFrame(final_list)
            
            current_path = os.path.dirname(os.path.abspath(__file__))
            save_dir = os.path.abspath(os.path.join(current_path, "../../data/raw"))
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, "master_data_2025.csv")
            
            df.to_csv(save_path, index=False, encoding="utf-8-sig")
            print(f"\n✨ 大功告成！數據已存至: {save_path}")
            print(f"統計：抓取到 {len(df)} 筆賽事歷史。")