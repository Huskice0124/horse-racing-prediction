import pandas as pd
import numpy as np
import re
from sklearn.ensemble import RandomForestClassifier

# 1. 載入資料
df = pd.read_csv(r'C:\Users\User\Desktop\horse_racing_project\data\raw\master_data_2025.csv')

# 2. 資料清洗
def clean_rank(x):
    try:
        return int(x)
    except:
        return np.nan

df['rank'] = df['着順'].apply(clean_rank)
df = df.dropna(subset=['rank'])
df['top3'] = (df['rank'] <= 3).astype(int)

# 3. 特徵挖掘 (Feature Engineering) [cite: 28]

# 解析馬體重 [cite: 29]
def parse_weight(x):
    if pd.isna(x) or x == '計不':
        return np.nan, 0
    match = re.search(r'(\d+)\(([\+\-]?\d+)\)', str(x))
    if match:
        return float(match.group(1)), float(match.group(2))
    else:
        try:
            return float(x), 0
        except:
            return np.nan, 0

df[['weight', 'weight_diff']] = df['馬体重'].apply(lambda x: pd.Series(parse_weight(x)))

# 解析性別 (若有性齢欄位請開啟，目前先保留邏輯)
def parse_sex(sex_age_str):
    if pd.isna(sex_age_str): return 0
    if '牝' in str(sex_age_str): return 1  # 母馬
    if 'セ' in str(sex_age_str): return 2  # 閹馬
    return 0
# df['sex'] = df['性齢'].apply(parse_sex)

# 處理東京 2000m 檔位陷阱 [cite: 5, 6, 7]
def gate_penalty(row):
    # 東京 2000m 第一個彎道極近，外檔 (7-8框) 劣勢顯著 [cite: 6]
    if '東京' in str(row['開催']) and row['距離'] == '芝2000':
        if row['枠番'] >= 7:
            return 1 
    return 0

df['is_outer_gate_penalty'] = df.apply(gate_penalty, axis=1)

# 轉換數值型與複合特徵
df['last_3f'] = pd.to_numeric(df['上り'], errors='coerce') # 修正原本的 coece 手誤
df['popularity'] = pd.to_numeric(df['人気'], errors='coerce')
df['burden_weight'] = pd.to_numeric(df['斤量'], errors='coerce')
df['gate'] = pd.to_numeric(df['枠番'], errors='coerce')
df['weight_ratio'] = df['burden_weight'] / df['weight']

# 計算近況：馬匹近三場平均表現
df['date'] = pd.to_datetime(df['日付'])
df = df.sort_values(['horse_name', 'date'])
df['avg_rank_last3'] = df.groupby('horse_name')['rank'].shift(1).rolling(window=3, min_periods=1).mean()
df['avg_last3f_last3'] = df.groupby('horse_name')['last_3f'].shift(1).rolling(window=3, min_periods=1).mean()

# 騎師勝率
jockey_win_rate = df.groupby('騎手')['top3'].mean().to_dict()
df['jockey_score'] = df['騎手'].map(jockey_win_rate)

# 填補缺失
df['avg_rank_last3'] = df['avg_rank_last3'].fillna(df['rank'].mean())
df['avg_last3f_last3'] = df['avg_last3f_last3'].fillna(df['last_3f'].mean())

# 4. 資料切割 [cite: 42]
target_race_mask = (df['レース名'].str.contains(r'天皇賞\(秋\)', na=False)) & (df['date'].dt.year == 2025)
df_test = df[target_race_mask].copy()
df_train = df[~target_race_mask].copy()

# 【重點修正】確保所有新特徵都進入 X_train
features = [
    'gate', 'burden_weight', 'popularity', 'avg_rank_last3', 
    'avg_last3f_last3', 'weight_diff', 'jockey_score',
    'is_outer_gate_penalty', 'weight_ratio' # 新加入的欄位
]

X_train = df_train[features].fillna(0)
y_train = df_train['top3']
X_test = df_test[features].fillna(0)

# 5. 模型訓練
model = RandomForestClassifier(n_estimators=500, max_depth=8, random_state=42)
model.fit(X_train, y_train)

# 6. 預測與排名
df_test['pred_prob'] = model.predict_proba(X_test)[:, 1]
df_test['predicted_rank'] = df_test['pred_prob'].rank(ascending=False, method='min').astype(int)

# 輸出結果分析 [cite: 51]
result = df_test[['horse_name', 'predicted_rank', 'rank', 'pred_prob', 'popularity']].sort_values('predicted_rank')
print("--- 2025 天皇賞(秋) 預測結果 ---")
print(result)

# 匯出結果 [cite: 42]
result.to_csv(r'C:\Users\User\Desktop\horse_racing_project\data\raw\tenno_sho_2025_predictions_v2.csv', index=False)