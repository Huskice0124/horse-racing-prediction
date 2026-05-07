import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import os
import random

# --- 1. 基礎映射與解析輔助 ---
WEATHER_MAP = {"晴": 1, "曇": 2, "小雨": 3, "雨": 4, "雪": 5}
TRACK_MAP = {"良": 1, "稍重": 2, "重": 3, "不良": 4}

def safe_get(cols, index):
    """防止欄位位移導致的 IndexError"""
    try:
        if index < len(cols):
            return cols[index].text.strip()
        return ""
    except:
        return ""

# --- 2. 核心功能：抓取出賽名單 ---
def get_entry_list(race_id):
    """抓取特定 Race ID 的參賽名單 [cite: 13, 18]"""
    url = f"https://db.netkeiba.com/race/{race_id}/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
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

# --- 3. [新增] 核心功能：抓取馬匹屬性與血統 (Feature Extension) ---
def scrape_horse_profile(h_id):
    """抓取馬匹個人主頁，提取性別、年齡與五代血統 [cite: 33, 34]"""
    url = f"https://db.netkeiba.com/horse/ped/{h_id}/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        time.sleep(random.uniform(1.2, 2.0))
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.content, "html.parser")
        
        profile = {"sex_age": "未知", "sire": "未知", "dam_sire": "未知"}
        
        # 提取性別年齡 (位於 db_prof_table) [cite: 25]
        prof_table = soup.find('table', class_='db_prof_table')
        if prof_table:
            for row in prof_table.find_all('tr'):
                th = row.find('th')
                if th and '性齢' in th.get_text():
                    profile["sex_age"] = row.find('td').get_text(strip=True)
                    break
        
        # 提取父系與母父系 (血統文本分析) [cite: 32]
        blood_table = soup.find('table', class_='blood_table')
        if blood_table:
            tds = blood_table.find_all('td')
            if len(tds) > 0:
                profile["sire"] = tds[0].get_text(strip=True) # 父系馬
            if len(tds) > 2:
                profile["dam_sire"] = tds[2].get_text(strip=True) # 母父系馬
                
        return profile
    except Exception as e:
        print(f"屬性抓取錯誤 (ID: {h_id}): {e}")
        return {"sex_age": "未知", "sire": "未知", "dam_sire": "未知"}

# --- 4. 核心功能：抓取歷史戰績 (智慧掃描版) ---
def scrape_horse_history(h_id, h_name):
    """抓取馬匹過去所有賽事紀錄 [cite: 21]"""
    url = f"https://db.netkeiba.com/horse/result/{h_id}/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        time.sleep(random.uniform(1.5, 2.5))
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, "html.parser", from_encoding="euc-jp")
        table = soup.find("table", class_="nk_tb_common")
        if not table: return None

        records = []
        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) < 15: continue

            row_data = {
                "horse_id": h_id,
                "horse_name": h_name,
                "日付": safe_get(cols, 0),
                "開催": safe_get(cols, 1),
                "天氣": safe_get(cols, 2),
                "R": safe_get(cols, 3),
                "レース名": safe_get(cols, 4),
                "頭数": "", "枠番": "", "馬番": "", "オッズ": "", "人氣": "", "着順": "",
                "騎手ID": "", "騎手": "", "斤量": "", "距離": "", "馬場": "", "タイム": "",
                "着差": "", "通過": "", "ペース": "", "上り": "", "馬體重": ""
            }

            # 處理欄位位移 (智慧偵測)
            idx = 5
            if len(cols) > 5 and not cols[5].text.strip().isdigit():
                idx = 6
            
            row_data["頭数"] = safe_get(cols, idx)
            row_data["枠番"] = safe_get(cols, idx+1)
            row_data["馬番"] = safe_get(cols, idx+2)
            row_data["オッズ"] = safe_get(cols, idx+3)
            row_data["人氣"] = safe_get(cols, idx+4)
            row_data["着順"] = safe_get(cols, idx+5)
            row_data["斤量"] = safe_get(cols, idx+7)

            # 騎手資訊
            j_col = cols[idx+6] if (idx+6) < len(cols) else None
            if j_col and j_col.find("a"):
                row_data["騎手ID"] = j_col.find("a")['href'].split('/')[-2]
                row_data["騎手"] = j_col.text.strip()

            # 特徵掃描：處理距離、馬場、上り 3F 等關鍵變數 [cite: 2, 28]
            time_idx = -1
            for i, col in enumerate(cols):
                txt = col.text.strip()
                if not txt or txt == "**": continue
                if re.match(r"^[芝ダ障].*\d{4}$", txt): row_data["距離"] = txt
                elif txt in ["良", "稍重", "重", "不良"]: row_data["馬場"] = txt
                elif re.match(r"^\d+:\d{2}\.\d$", txt):
                    row_data["タイム"] = txt
                    time_idx = i
                elif re.match(r"^\d{2}\.\d$", txt): row_data["上り"] = txt
                elif re.match(r"^\d{3}(\([+-]?\d*\))?$", txt): row_data["馬體重"] = txt
                elif re.match(r"^\d{2}\.\d-\d{2}\.\d$", txt): row_data["ペース"] = txt
                elif re.match(r"^\d+(-\d+)+$", txt): row_data["通過"] = txt

            if time_idx != -1:
                row_data["着差"] = safe_get(cols, time_idx + 1)

            records.append(row_data)
        return records
    except Exception as e: 
        print(f"戰績抓取錯誤 ({h_name}): {e}")
        return None

# --- 5. 主執行流程 ---
if __name__ == "__main__":
    RACE_ID = "202505041111" # 2025 天皇賞(秋) [cite: 18]
    print(f"🚀 開始特徵補全任務，目標：{RACE_ID}")
    
    entries = get_entry_list(RACE_ID)
    if not entries:
        print("❌ 無法獲取出賽名單。")
    else:
        print(f"✅ 成功獲取 {len(entries)} 匹馬名單。")
        final_dataset = []
        
        for horse in entries:
            print(f"--- 挖掘中: {horse['h_name']} ---")
            
            # 第一步：獲取身分證 (性別、血統)
            profile = scrape_horse_profile(horse['h_id'])
            
            # 第二步：獲取歷史履歷 (戰績)
            history = scrape_horse_history(horse['h_id'], horse['h_name'])
            
            if history:
                # 第三步：將身分證特徵整合進每一筆賽事中
                for record in history:
                    record["性齢"] = profile["sex_age"]
                    record["父系"] = profile["sire"]
                    record["母父系"] = profile["dam_sire"]
                final_dataset.extend(history)
        
        # 儲存為 CSV [cite: 42]
        if final_dataset:
            df = pd.DataFrame(final_dataset)
            save_dir = os.path.join(os.path.dirname(__file__), "../../data/raw")
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, "master_data_2025_v2.csv")
            
            df.to_csv(save_path, index=False, encoding="utf-8-sig")
            print(f"\n✨ 任務完成！數據已存至: {save_path}")
            print(f"總計抓取筆數: {len(df)}")