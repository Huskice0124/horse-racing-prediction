import pandas as pd
import numpy as np
import re
from sklearn.ensemble import RandomForestClassifier

# 1. 載入資料
df = pd.read_csv(r'C:\Users\User\Desktop\horse_racing_project\data\raw\master_data_2025.csv')

# 2. 資料清洗與標籤定義 (Target)
def clean_rank(x):
    try:
        return int(x)
    except:
        return np.nan

# 建立預測目標：前三名為 1，其餘為 0 
df['rank'] = df['着順'].apply(clean_rank)
df = df.dropna(subset=['rank'])
df['top3'] = (df['rank'] <= 3).astype(int)

# 3. 特徵挖掘 (Feature Engineering) [cite: 28]
# 解析馬體重與體重變化 [cite: 29]
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

# 轉換數值型欄位
df['last_3f'] = pd.to_numeric(df['上り'], errors='coerce')
df['popularity'] = pd.to_numeric(df['人気'], errors='coerce')
df['burden_weight'] = pd.to_numeric(df['斤量'], errors='coerce')
df['gate'] = pd.to_numeric(df['枠番'], errors='coerce')

# 計算近況：馬匹近三場平均名次 
df['date'] = pd.to_datetime(df['日付'])
df = df.sort_values(['horse_name', 'date'])
df['avg_rank_last3'] = df.groupby('horse_name')['rank'].shift(1).rolling(window=3, min_periods=1).mean()
df['avg_last3f_last3'] = df.groupby('horse_name')['last_3f'].shift(1).rolling(window=3, min_periods=1).mean()

# 計算騎師勝率特徵 
jockey_win_rate = df.groupby('騎手')['top3'].mean().to_dict()
df['jockey_score'] = df['騎手'].map(jockey_win_rate)

# 填補缺失值
df['avg_rank_last3'] = df['avg_rank_last3'].fillna(df['rank'].mean())
df['avg_last3f_last3'] = df['avg_last3f_last3'].fillna(df['last_3f'].mean())

# 4. 資料切割 (2025 天皇賞秋作為測試集) [cite: 42]
target_race_mask = (df['レース名'].str.contains(r'天皇賞\(秋\)', na=False)) & (df['date'].dt.year == 2025)
df_test = df[target_race_mask].copy()
df_train = df[~target_race_mask].copy()

# 選擇特徵矩陣
features = ['gate', 'burden_weight', 'popularity', 'avg_rank_last3', 'avg_last3f_last3', 'weight_diff', 'jockey_score']
X_train = df_train[features].fillna(0)
y_train = df_train['top3']
X_test = df_test[features].fillna(0)

# 5. 模型訓練 (Random Forest) 
from sklearn.linear_model import LogisticRegression

# 第一步：建立模型實例
model = LogisticRegression() 

# 第二步：一定要有這一行！讓模型讀取訓練資料 (fit)
# 如果這一行被註解掉或漏掉，就會報出 NotFittedError
model.fit(X_train, y_train)

# 6. 預測與排名
df_test['pred_prob'] = model.predict_proba(X_test)[:, 1]
df_test['predicted_rank'] = df_test['pred_prob'].rank(ascending=False, method='min').astype(int)

# 輸出結果
result = df_test[['horse_name', 'predicted_rank', 'rank', 'pred_prob', 'popularity']].sort_values('predicted_rank')
print(result)

# 匯出至 CSV 供後續分析 [cite: 42]
result.to_csv(r'C:\Users\User\Desktop\horse_racing_project\data\raw\tenno_sho_2025_predictions.csv', index=False)