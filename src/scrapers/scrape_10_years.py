import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os

def find_tenno_sho_id(year):
    """
    自動尋找該年度「天皇賞(秋)」的 Race ID
    規則：東京(05) 4回(04) 第1~12日 11R
    """
    print(f"🔍 尋找 {year} 年的天皇賞(秋) ID...")
    
    # 擴大天數範圍：從 01 掃描到 12 (包含你看到的 11)
    for day in [f"{i:02d}" for i in range(1, 13)]: 
        race_id = f"{year}0504{day}11"
        url = f"https://db.netkeiba.com/race/{race_id}/"
        try:
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.3 Safari/605.1.15"}, timeout=5)
            res.encoding = 'EUC-JP'
            soup = BeautifulSoup(res.content, "html.parser")
            
            # 檢查網頁標題是否包含「天皇賞(秋)」
            title = soup.find("title")
            if title and "天皇賞(秋)" in title.text:
                print(f"🎯 成功鎖定 {year} 年 ID: {race_id}")
                return race_id
        except Exception as e:
            pass
        
        time.sleep(1) # 禮貌性延遲，避免被鎖 IP
    
    print(f"❌ 找不到 {year} 年的資料")
    return None

def scrape_race_result(race_id, year):
    """抓取單場賽事的所有名次與成績"""
    url = f"https://db.netkeiba.com/race/{race_id}/"
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.3 Safari/605.1.15"}, timeout=10)
        res.encoding = 'EUC-JP'
        soup = BeautifulSoup(res.content, "html.parser")
        
        table = soup.find("table", class_="race_table_01")
        if not table: return []

        records = []
        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) < 15: continue
            
            # 完賽時間轉換 (例如 1:58.6 -> 118.6)
            time_str = cols[7].text.strip()
            time_sec = None
            if ":" in time_str:
                try:
                    m, s = time_str.split(":")
                    time_sec = int(m) * 60 + float(s)
                except:
                    pass
            #for i in range(len(cols)):
            #    print("index: ",i,cols[i]) #for debugging
            records.append({
                "年度": year,
                "着順": cols[0].text.strip(),
                "枠番": cols[1].text.strip(),
                "馬番": cols[2].text.strip(),
                "馬名": cols[3].text.strip(),
                "性齢": cols[4].text.strip(),
                "斤量": cols[5].text.strip(),
                "騎手": cols[6].text.strip(),
                "タイム": time_str,
                "タイム(秒)": time_sec,
                "着差": cols[8].text.strip(),
                "通過": cols[14].text.strip(),
                "上り3F": cols[15].text.strip(),
                "単勝": cols[16].text.strip(),
                "人気": cols[17].text.strip(),
                "馬体重": cols[18].text.strip()
            })
        #print(records)
        return records
    except Exception as e:
        print(f"抓取 {year} 年賽果時發生錯誤: {e}")
        return []

if __name__ == "__main__":
    print("🚀 開始執行：天皇賞(秋) 過去 10 年資料大匯總！\n")
    
    all_years_data = []
    # 抓取 2015 到 2024 年 (剛好 10 年)
    for target_year in range(2005, 2026):
        r_id = find_tenno_sho_id(target_year)
        if r_id:
            # 找到 ID 後就進去抓成績
            print(f"   => 正在下載 {target_year} 年賽果...")
            race_data = scrape_race_result(r_id, target_year)
            all_years_data.extend(race_data)
            time.sleep(2) # 喝口水再抓下一年
            
    # 存檔
    if all_years_data:
        df = pd.DataFrame(all_years_data)
        
        # 自動存到你的 data/raw 目錄
        current_path = os.path.dirname(os.path.abspath(__file__))
        save_dir = os.path.abspath(os.path.join(current_path, "../../data/raw"))
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, "tenno_sho_10_years.csv")
        
        df.to_csv(save_path, index=False, encoding="utf-8-sig")
        print(f"\n✨ 大功告成！總共抓取了 {len(df)} 筆參賽紀錄。")
        print(f"📁 檔案已妥善存至: {save_path}")