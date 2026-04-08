import pandas as pd

# 1. 讀取資料
df_horse = pd.read_csv("../../data/raw/master_data_2025.csv")
df_jockey = pd.read_csv("../../data/processed/jockey_stats.csv")

# 2. 合併 (以 jockey_id 為基準)
# 注意：確保你的 master_data 裡有 jockey_id 欄位
final_df = pd.merge(df_horse, df_jockey, left_on="jockey_id", right_on="j_id", how="left")

# 3. 計算騎師勝率 (Win Rate)
final_df["j_win_rate"] = final_df["wins"] / final_df["total_races"]

# 4. 處理馬體重缺失值 (插值法)
# 這是你之前提到的：取前後場次平均或中位數 [cite: 26]
final_df["weight"] = final_df.groupby("horse_id")["weight"].transform(lambda x: x.fillna(x.mean()))

# 5. 儲存最終建模用資料
final_df.to_csv("../../data/final/training_data.csv", index=False)
print("建模用最終資料表已產出！")