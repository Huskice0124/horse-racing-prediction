import pandas as pd
import lightgbm as lgb
import os

# --- 1. 路徑配置 ---
BASE_DIR = r"C:\Users\User\Desktop\horse_racing_project"
MASTER_PATH = os.path.join(BASE_DIR, r"data\raw\master_data_2025_v2.csv")
JOCKEY_PATH = os.path.join(BASE_DIR, r"data\processed\jockey_stats_final.csv")
OUTPUT_PATH = os.path.join(BASE_DIR, r"output\tenno_sho_final_predictions.csv")

def train_and_export_results():
    # 載入主表與騎手數據 (強制 ID 為字串以保留 0)
    df = pd.read_csv(MASTER_PATH, dtype={'jockey_id': str})
    j_df = pd.read_csv(JOCKEY_PATH, dtype={'jockey_id': str})
    
    # 合併騎手勝率
    df = df.merge(j_df[['jockey_id', 'career_win_rate']], on='jockey_id', how='left')
    
    # 2. 定義核心特徵與目標
    # 權重調整：人氣(300), 體重(250), 近況(250), 檔位(220), 騎手(179), 斤量(132), 年齡(65), 性別(24)
    features = [
        'popularity', 'weight_val', 'avg_rank_3', 'gate', 
        'career_win_rate', 'weight_carried', 'age', 'sex_code'
    ]
    X = df[features]
    y = df['rank_num'] # 實際著名次

    # 3. 訓練 LightGBM 模型
    params = {
        'objective': 'regression', 
        'metric': 'rmse', 
        'verbosity': -1, 
        'seed': 42,
        'learning_rate': 0.05
    }
    train_data = lgb.Dataset(X, label=y)
    model = lgb.train(params, train_data, num_boost_round=250)

    # 4. 產出預測值與「分數來源」總結
    df['predicted_score'] = model.predict(X)
    
    # 定義本次專案設定的目標權重作為分數來源說明
    # 這樣在 CSV 與 Streamlit 儀表板中能清晰展現分析邏輯
    target_weights = {
        'popularity': 500, 
        'weight_val': 250, 
        'avg_rank_3': 250, 
        'gate': 220, 
        'career_win_rate': 179, 
        'weight_carried': 132, 
        'age': 65, 
        'sex_code': 24
    }
    source_summary = ", ".join([f"{f}({w})" for f, w in target_weights.items()])
    df['score_source_weights'] = source_summary

    # 5. 排序並增加排名順序
    # 預測名次越小（分值越低）代表越看好
    result_df = df.sort_values(by='predicted_score')
    result_df['final_rank'] = range(1, len(result_df) + 1)

    # 6. 儲存為 CSV
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    export_cols = [
        'final_rank', 'horse_name', 'jockey_name', 'predicted_score', 
        'popularity', 'weight_val', 'avg_rank_3', 'gate', 'score_source_weights'
    ]
    
    # 使用 utf-8-sig 確保 Excel 開啟日文不亂碼
    result_df[export_cols].to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    
    print(f"✨ 權重更新完成！預測結果已儲存至: {OUTPUT_PATH}")
    return result_df[export_cols].head(10)

if __name__ == "__main__":
    top_10 = train_and_export_results()
    print("\n--- 2026 天皇賞(秋) 預測排行榜 (Top 10) ---")
    print(top_10.to_string(index=False))