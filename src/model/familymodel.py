import pandas as pd
import numpy as np
import os

# --- 1. 路徑設定 ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RACE_DATA_PATH = os.path.join(BASE_DIR, 'data', 'raw', 'master_data_2025_v2.csv')
JOCKEY_STATS_PATH = r'C:\Users\User\Desktop\horse_racing_project\data\processed\jockey_stats_final.csv'

def generate_connected_ranking(race_path, jockey_path):
    print("🚀 正在啟動綜合排序模型...")
    
    # 讀取數據
    df = pd.read_csv(race_path, on_bad_lines='skip')
    j_df = pd.read_csv(jockey_path)
    
    # --- 修正：動態選取騎手欄位，避免 Length mismatch ---
    # 我們假設前兩個欄位是『騎手名稱』與『勝率』，或者手動指定索引
    print(f"📊 偵測到騎手檔案原始欄位數: {len(j_df.columns)}")
    
    # 這裡我們只取前兩個欄位，並重新命名
    jockey_data = j_df.iloc[:, [0, 1]].copy() 
    jockey_data.columns = ['騎手', 'jockey_win_rate']
    
    # 數據轉型以利連結
    df['騎手'] = df['騎手'].astype(str).str.strip()
    jockey_data['騎手'] = jockey_data['騎手'].astype(str).str.strip()
    
    # 合併騎手勝率到馬匹數據
    combined_df = df.merge(jockey_data, on='騎手', how='left')
    combined_df['jockey_win_rate'] = combined_df['jockey_win_rate'].fillna(0.1) # 沒數據的給預設值

    # --- 2. 建立『人馬合一』權重公式 ---
    # 分數越低 = 實力越強 (名次越靠前)
    def calculate_combined_index(row):
        # 馬匹血統分 (天賦)
        sire = str(row['父系'])
        sire_score = 0.8 if 'キタサンブラック' in sire else (0.9 if 'ドゥラメンテ' in sire else 1.0)
        
        # 騎手勝率分 (技術) - 勝率越高，減分越多 (有利排名)
        jockey_bonus = row['jockey_win_rate'] * 5 
        
        # 人氣分 (市場預期)
        popularity = pd.to_numeric(row['人氣'], errors='coerce')
        if pd.isna(popularity): popularity = 10
        
        # 最終權重公式
        return (popularity * 1.2) + (sire_score * 0.5) - jockey_bonus

    combined_df['綜合競爭力指數'] = combined_df.apply(calculate_combined_index, axis=1)

    # --- 3. 執行排序：從上到下 (由強至弱) ---
    # 只取出最新一場賽事的馬匹組合 (去除重複的歷史紀錄)
    final_list = combined_df.drop_duplicates(subset=['horse_name'])
    final_list = final_list.sort_values(by='綜合競爭力指數', ascending=True)

    return final_list[['horse_name', '騎手', 'jockey_win_rate', '父系', '綜合競爭力指數']]

# --- 4. 執行與輸出 ---
try:
    ranking_report = generate_connected_ranking(RACE_DATA_PATH, JOCKEY_STATS_PATH)
    
    print("\n🏆 2025 天皇賞(秋) 綜合實力排行榜 (由上至下排序)")
    print("="*85)
    print(f"{'排名':<5} {'馬匹名稱':<18} {'騎手':<12} {'勝率':<10} {'綜合指數'}")
    print("-"*85)
    
    for i, (idx, row) in enumerate(ranking_report.iterrows(), 1):
        print(f"{i:<5} {row['horse_name']:<18} {row['騎手']:<12} {row['jockey_win_rate']:<10.2%} {row['綜合競爭力指數']:.2f}")
    
    # 存檔供報告使用
    ranking_report.to_csv('horse_jockey_combined_ranking.csv', index=False, encoding='utf-8-sig')
    print(f"\n✨ 排序結果已存至: horse_jockey_combined_ranking.csv")

except Exception as e:
    print(f"❌ 執行失敗: {e}")