import pandas as pd
import lightgbm as lgb
import os

# --- 1. 路徑設定與資料載入 ---
BASE_DIR = r"C:\Users\User\Desktop\horse_racing_project"
MASTER_PATH = os.path.join(BASE_DIR, r"data\raw\master_data_2025_v2.csv")
JOCKEY_PATH = os.path.join(BASE_DIR, r"data\processed\jockey_stats_final.csv")

def train_and_predict_model():
    # 載入資料，並強制將 jockey_id 設為字串以保留開頭的 0
    df = pd.read_csv(MASTER_PATH, dtype={'jockey_id': str})
    jockey_df = pd.read_csv(JOCKEY_PATH, dtype={'jockey_id': str})
    
    # 2. 資料合併與型態轉換
    # 關聯騎手勝率特徵
    df = df.merge(jockey_df[['jockey_id', 'career_win_rate']], on='jockey_id', how='left')
    
    # [關鍵修正]：將血統與性別轉換為 category 型態，模型才能讀取
    df['sire_line'] = df['sire_line'].astype('category')
    df['sex_code'] = df['sex_code'].astype('category')
    
    # 3. 定義特徵清單 (確保包含 sire_line)
    features = [
        'popularity',      # 人氣 
        'career_win_rate', # 騎手勝率 
        'weight_carried',  # 斤量 
        'age',             # 年齡 
        'sex_code',        # 性別代碼 
        'weight_val',      # 體重數值
        'avg_rank_3',      # 過去三場平均名次 
        'gate',            # 檔位 
        'sire_line'        # 血統系統 (修復報錯點) 
    ]
    
    X = df[features]
    y = df['rank_num'] # 預測目標：實際著順

    # 4. 模型參數與訓練
    params = {
        'objective': 'regression',
        'metric': 'rmse',
        'learning_rate': 0.05,
        'feature_fraction': 0.9,
        'bagging_fraction': 0.8,
        'seed': 42,
        'verbosity': -1
    }
    
    # 在這裡指定哪些欄位是類別型變數
    train_data = lgb.Dataset(X, label=y, categorical_feature=['sire_line', 'sex_code'])
    
    print("🚀 正在訓練全維度預測模型...")
    model = lgb.train(params, train_data, num_boost_round=200)

    # 5. 輸出最新的特徵重要性
    importance = pd.DataFrame({'Feature': features, 'Importance': model.feature_importance()})
    print("\n--- 最新特徵重要性排序 ---")
    print(importance.sort_values(by='Importance', ascending=False))
    
    return model

if __name__ == "__main__":
    model = train_and_predict_model()