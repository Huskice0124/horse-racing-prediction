import requests
from bs4 import BeautifulSoup
import pandas as pd
import time, random, os, re

def get_all_jockey_ids_from_race(race_id):
    """
    從比賽頁面自動獲取所有參賽騎師的 ID 與姓名
    """
    url = f"https://db.netkeiba.com/race/{race_id}/"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'EUC-JP'
        soup = BeautifulSoup(res.content, "html.parser")
        table = soup.find("table", class_="race_table_01")
        
        jockey_list = []
        rows = table.find_all("tr")[1:] # 跳過表頭
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 7: continue
            
            # 騎師連結通常在第 7 個 td (index 6)
            j_tag = cols[6].find("a")
            if j_tag:
                j_id = j_tag['href'].split('/')[-2]
                j_name = j_tag.text.strip()
                jockey_list.append({"j_id": j_id, "j_name": j_name})
        
        # 去除重複的騎師 (有些騎師可能在一場比賽騎多匹馬，雖然 G1 不常見)
        unique_jockeys = {v['j_id']: v for v in jockey_list}.values()
        return list(unique_jockeys)
    except Exception as e:
        print(f"❌ 無法獲取比賽名單: {e}")
        return []

def get_jockey_lifetime_stats(j_id):
    """
    精確抓取騎師生涯數據：1着(勝數) 與 騎乘回數(總場數)
    """
    url = f"https://db.netkeiba.com/jockey/{j_id}/"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        time.sleep(random.uniform(1.5, 2.5))
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.content, "html.parser", from_encoding="euc-jp")
        
        for table in soup.find_all("table", class_="nk_tb_common"):
            for row in table.find_all("tr"):
                cols = row.find_all("td")
                # 根據診斷檔案：第一格 td[0] 必須是「累計」
                if cols and "累計" in cols[0].text:
                    # 索引校正：td[2]是勝場，td[6]是總場數
                    wins = int(cols[2].text.strip().replace(',', ''))
                    total = int(cols[6].text.strip().replace(',', ''))
                    return wins, total
    except: pass
    return 0, 0

def main():
    RACE_ID = "202505041111"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.abspath(os.path.join(base_dir, "../../data/processed"))
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"🚀 正在從比賽 {RACE_ID} 提取騎師清單...")
    jockeys = get_all_jockey_ids_from_race(RACE_ID)
    print(f"✅ 找到 {len(jockeys)} 位參賽騎師。")

    results = []
    for j in jockeys:
        print(f"正在分析騎師: {j['j_name']} ({j['j_id']})...")
        wins, total = get_jockey_lifetime_stats(j['j_id'])
        results.append({
            "jockey_id": j['j_id'],
            "jockey_name": j['j_name'],
            "career_wins": wins,
            "career_total_rides": total,
            "career_win_rate": round(wins/total, 4) if total > 0 else 0
        })
        if wins > 0:
            print(f"   [OK] 生涯勝數: {wins}")
        else:
            print(f"   [!] 未抓到有效數據")

    if results:
        df = pd.DataFrame(results)
        save_path = os.path.join(output_dir, "jockey_stats_final.csv")
        df.to_csv(save_path, index=False, encoding="utf-8-sig")
        print("-" * 30)
        print(f"✨ 成功！已儲存 {len(df)} 位騎師數據至：{save_path}")

if __name__ == "__main__":
    main()