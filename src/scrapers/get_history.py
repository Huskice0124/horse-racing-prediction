import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import os
import random

WEATHER_MAP = {"晴": 1, "曇": 2, "小雨": 3, "雨": 4, "雪": 5}
TRACK_MAP = {"良": 1, "稍重": 2, "重": 3, "不良": 4}

def safe_get(cols, index):
    try:
        if index < len(cols): return cols[index].text.strip()
        return ""
    except: return ""

def get_entry_list(race_id):
    """抓取特定 Race ID 的完整參賽名單"""
    url = f"https://db.netkeiba.com/race/{race_id}/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'EUC-JP'
        soup = BeautifulSoup(res.content, "html.parser")
        
        table = soup.find("table", class_="nk_tb_common")
        if not table:
            table = soup.find("table", class_="race_table_01")
            
        if not table: 
            print(f"⚠️ 找不到賽事表格 (ID: {race_id})")
            return []
        
        entries = []
        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) < 4: continue
            
            h_link = None
            j_link = None
            for a in row.find_all("a"):
                if "/horse/" in a['href']: h_link = a
                if "/jockey/" in a['href']: j_link = a
                
            if h_link and j_link:
                entries.append({
                    "h_id": h_link['href'].split('/')[-2],
                    "h_name": h_link.text.strip(),
                    "j_id": j_link['href'].split('/')[-2],
                    "j_name": j_link.text.strip()
                })
        return entries
    except Exception as e:
        print(f"❌ 名單抓取錯誤: {e}")
        return []

def scrape_horse_profile(h_id):
    """抓取馬匹血統與生理數據（內建安全網頁檢測）"""
    url = f"https://db.netkeiba.com/horse/ped/{h_id}/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        # 🌟 安全防禦機制：拉長間隔防止被鎖
        time.sleep(random.uniform(2.5, 4.5)) 
        res = requests.get(url, headers=headers, timeout=10)
        
        # 🚨 診斷日誌：如果是 403 代表被官方伺服器阻擋了
        if res.status_code == 403:
            print(f" 🚫 [血統網頁] 遭 netkeiba 封鎖 (403 Forbidden)！將跳過此馬。")
            return None
            
        res.encoding = 'EUC-JP'
        soup = BeautifulSoup(res.content, "html.parser")
        profile = {"sex_age": "未知", "sire": "未知", "dam_sire": "未知"}
        
        txt01 = soup.find('p', class_='txt_01')
        if txt01:
            raw_info = txt01.get_text(strip=True)
            match = re.search(r'([牡牝騸]\d+歳)', raw_info)
            if match: profile["sex_age"] = match.group(1)
        
        blood_table = soup.find('table', class_='blood_table')
        if blood_table:
            tds = blood_table.find_all('td')
            if len(tds) > 0: profile["sire"] = tds[0].get_text(strip=True)
            if len(tds) > 2: profile["dam_sire"] = tds[2].get_text(strip=True)
        return profile
    except Exception as e:
        return None

def scrape_horse_history(h_id, h_name):
    """抓取馬匹歷史戰績（內建安全狀態診斷）"""
    url = f"https://db.netkeiba.com/horse/result/{h_id}/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        time.sleep(random.uniform(2.5, 4.5))
        res = requests.get(url, headers=headers, timeout=15)
        
        if res.status_code == 403:
            print(f" 🚫 [戰績網頁] 遭 netkeiba 封鎖 (403 Forbidden)！無法讀取 {h_name}。")
            return None
            
        soup = BeautifulSoup(res.content, "html.parser", from_encoding="euc-jp")
        table = soup.find("table", class_="nk_tb_common")
        if not table: return None

        records = []
        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) < 15: continue

            row_data = {
                "horse_id": h_id, "horse_name": h_name,
                "日付": safe_get(cols, 0), "開催": safe_get(cols, 1), "天氣": safe_get(cols, 2),
                "R": safe_get(cols, 3), "レース名": safe_get(cols, 4),
                "頭数": "", "枠番": "", "馬番": "", "オッズ": "", "人氣": "", "着順": "",
                "騎手ID": "", "騎手": "", "斤量": "", "距離": "", "馬場": "", "タイム": "",
                "着差": "", "通過": "", "ペース": "", "上り": "", "馬體重": ""
            }

            idx = 5
            if len(cols) > 5 and not cols[5].text.strip().isdigit(): idx = 6
            
            row_data["頭数"] = safe_get(cols, idx)
            row_data["枠番"] = safe_get(cols, idx+1)
            row_data["馬番"] = safe_get(cols, idx+2)
            row_data["オッズ"] = safe_get(cols, idx+3)
            row_data["人氣"] = safe_get(cols, idx+4)
            row_data["着順"] = safe_get(cols, idx+5)
            row_data["斤量"] = safe_get(cols, idx+7)

            j_col = cols[idx+6] if (idx+6) < len(cols) else None
            if j_col and j_col.find("a"):
                row_data["騎手ID"] = j_col.find("a")['href'].split('/')[-2]
                row_data["騎手"] = j_col.text.strip()

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

            if time_idx != -1: row_data["着差"] = safe_get(cols, time_idx + 1)
            records.append(row_data)
        return records
    except Exception as e: 
        return None

if __name__ == "__main__":
    TARGET_YEARS = [2022, 2023, 2024, 2025] 
    
    TENNO_SHO_AUTUMN_MAP = {
        2022: "202205040811",
        2023: "202305040811",
        2024: "202405040811",
        2025: "202505041111"
    }
    
    all_years_dataset = []
    crawled_horse_ids = set()
    
    for year in TARGET_YEARS:
        RACE_ID = TENNO_SHO_AUTUMN_MAP.get(year)
        if not RACE_ID: continue
            
        print(f"\n📁 ===========================================")
        print(f"🎬 開始下載 【{year} 年 天皇賞(秋)】 出賽名單...")
        print(f"=============================================")
        entries = get_entry_list(RACE_ID)
        
        if not entries:
            print(f"❌ 無法獲取 {year} 年名單。")
            continue
            
        print(f"✅ 成功找到 {year} 年當屆 {len(entries)} 匹馬！開始依序安全解鎖...")
        
        for i, horse in enumerate(entries, 1):
            is_new = horse['h_id'] not in crawled_horse_ids
            
            if is_new:
                crawled_horse_ids.add(horse['h_id'])
                print(f" ⏳ [{i}/{len(entries)}] 正在安全下載: {horse['h_name']}...")
                
                profile = scrape_horse_profile(horse['h_id'])
                # 如果被阻擋導致 profile 回傳 None，就暫時給予預設值避免崩潰
                if profile is None:
                    profile = {"sex_age": "未知", "sire": "未知", "dam_sire": "未知"}
                    
                history = scrape_horse_history(horse['h_id'], horse['h_name'])
                
                if history:
                    for record in history:
                        record["性齢"] = profile["sex_age"]
                        record["父系"] = profile["sire"]
                        record["母父系"] = profile["dam_sire"]
                    all_years_dataset.extend(history)
                    print(f"   🔹 {horse['h_name']} 歷史履歷下載成功 (共 {len(history)} 筆戰績)")
            else:
                print(f" 🔁 馬匹重疊：{horse['h_name']} 在前幾年已完成特徵採集，跳過。")

    if all_years_dataset:
        df = pd.DataFrame(all_years_dataset)
        save_dir = r"C:\Users\User\Desktop\horse_racing_project\data\raw"
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, "master_data_multi_year.csv")
        
        df.to_csv(save_path, index=False, encoding="utf-8-sig")
        print(f"\n✨ 【大功告成】多年份歷史特徵庫已安全覆蓋生成：{save_path}")
        print(f"📊 總計儲存戰績大數據：{len(df)} 筆。現在你可以重新打開 Streamlit 看精準分流了！")
    else:
        print("❌ 過程中未抓取到任何有效數據。")