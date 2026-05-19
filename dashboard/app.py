import streamlit as st
import pandas as pd
import numpy as np
import os
import re

# --- 1. 環境與 LightGBM 檢查 ---
try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    HAS_LGB = False

st.set_page_config(page_title="決戰天皇賞（秋）AI 預測系統", layout="wide", initial_sidebar_state="expanded")

# --- 2. 雙重路徑與多檔案相容配置 ---
BASE_DIR = r"C:\Users\User\Desktop\horse_racing_project"
JOCKEY_PATH_ABS = os.path.join(BASE_DIR, r"data\processed\jockey_stats_final.csv")
JOCKEY_PATH_REL = os.path.join("data", "processed", "jockey_stats_final.csv")

@st.cache_data
def load_and_clean_data():
    possible_master_paths = [
        os.path.join("data", "raw", "master_data_multi_year.csv"),
        os.path.join(BASE_DIR, r"data\raw\master_data_multi_year.csv"),
        os.path.join("data", "raw", "master_data_2025_v2.csv"),
        os.path.join(BASE_DIR, r"data\raw\master_data_2025_v2.csv"),
    ]
    
    m_path = None
    for path in possible_master_paths:
        if os.path.exists(path):
            m_path = path
            break
            
    j_path = JOCKEY_PATH_REL if os.path.exists(JOCKEY_PATH_REL) else JOCKEY_PATH_ABS
    
    if not m_path or not os.path.exists(j_path):
        st.error(f"❌ 找不到數據檔案！請確認爬蟲是否已生成 CSV。")
        return None
    
    # 讀取原始數據
    df = pd.read_csv(m_path, dtype=str) # 先全字串讀入，防止 ID 補零丟失
    j_df = pd.read_csv(j_path, dtype=str)
    
    # 🌟 核心防禦：自動清除所有欄位名稱前後的隱形空格
    df.columns = df.columns.str.strip()
    j_df.columns = j_df.columns.str.strip()
    
    st.sidebar.info(f"📊 數據庫載入成功：{os.path.basename(m_path)}")
    
    # 🌟 核心防禦：不論是新爬蟲的日文還是舊爬蟲的英文，通通強制對齊成標準標籤
    rename_dict = {
        '檢索ID': 'jockey_id', '騎手ID': 'jockey_id', '騎手id': 'jockey_id',
        '騎手': 'jockey_name',
        '人氣': 'popularity', '人気': 'popularity',
        '着順': 'rank_num', '著順': 'rank_num',
        '枠番': 'gate', '檔位': 'gate',
        '斤量': 'weight_carried'
    }
    df = df.rename(columns=rename_dict)
    j_df = j_df.rename(columns=rename_dict)
    
    # 🚨 終極診斷：如果真的還是缺 jockey_id，直接在網頁畫面上明明白白印出欄位給你看
    if 'jockey_id' not in df.columns:
        st.error(f"❌ 嚴重錯誤：主數據中找不到騎手 ID 欄位！目前的欄位有：{list(df.columns)}")
        return None
    if 'jockey_id' not in j_df.columns:
        st.error(f"❌ 嚴重錯誤：騎師數據中找不到 jockey_id 欄位！目前的欄位有：{list(j_df.columns)}")
        return None

    # 特徵工程 A：從馬體重中提取純數字
    if 'weight_val' not in df.columns and '馬體重' in df.columns:
        def extract_weight_val(x):
            if pd.isna(x): return np.nan
            match = re.search(r'(\d+)', str(x))
            return float(match.group(1)) if match else np.nan
        df['weight_val'] = df['馬體重'].apply(extract_weight_val)
        
    # 特徵工程 B：解析「性齢」
    if 'sex_code' not in df.columns and '性齢' in df.columns:
        def parse_sex_age_text(x):
            if pd.isna(x): return 1, 4.0
            s_code = 1 if '牡' in str(x) else 2 if '牝' in str(x) else 3
            match = re.search(r'(\d+)', str(x))
            age_val = float(match.group(1)) if match else 4.0
            return s_code, age_val
        df['sex_code'] = df['性齢'].apply(lambda x: parse_sex_age_text(x)[0])
        df['age'] = df['性齢'].apply(lambda x: parse_sex_age_text(x)[1])
        
    # 特徵工程 C：著順清洗
    df['rank_num_clean'] = pd.to_numeric(df['rank_num'], errors='coerce').fillna(10)
    
    # 特徵工程 D：動態滾動計算近況動態 avg_rank_3
    if 'avg_rank_3' not in df.columns:
        df = df.sort_values(by=['horse_id', '日付'])
        df['avg_rank_3'] = df.groupby('horse_id')['rank_num_clean'].transform(
            lambda x: x.shift(1).rolling(3, min_periods=1).mean()
        )
        df['avg_rank_3'] = df['avg_rank_3'].fillna(df['rank_num_clean'])
    
    df['rank_num'] = df['rank_num_clean']
    
    # 進行安全對齊合併
    df = df.merge(j_df[['jockey_id', 'career_win_rate']], on='jockey_id', how='left')
    
    # 強制將特徵轉為數值型態
    numeric_cols = ['popularity', 'weight_val', 'avg_rank_3', 'gate', 'weight_carried', 'age', 'sex_code', 'career_win_rate']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].fillna(df[col].mean())
            
    return df

# 正確呼叫位置（新代碼的第 88 行附近）

df_master = load_and_clean_data()

if df_master is not None:
    # --- 3. 側邊欄控制面板 ---
    st.sidebar.title("🏇 預測核心控制台")
    st.sidebar.markdown("---")
    
    # 🚀 升級：擴充歷史回測年份對照表（包含官方精準比賽日期）
    # 🚀 完美精簡版：只保留資料最完整的 2024 與 2025 戰局
    RACE_YEAR_MAP = {
        "2025年 天皇賞・秋 (完整預測陣容)": {"date": "2025/11/02", "desc": "2025/11/02 | 混合新星崛起之戰"},
        "2024年 天皇賞・秋 (精英縱向回測)": {"date": "2024/10/27", "desc": "2024/10/27 | 亞軍『タスティエーラ』爆冷平反戰"}
    }
    
    selected_label = st.sidebar.selectbox("📅 選擇回測/預測目標年份", list(RACE_YEAR_MAP.keys()))
    target_date = RACE_YEAR_MAP[selected_label]["date"]
    race_description = RACE_YEAR_MAP[selected_label]["desc"]
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎛️ 文理融合：動態權重模擬")
    st.sidebar.caption("調整滑桿，即時改變右側「自定義模型」的評分洗牌！")
    
    w_pop = st.sidebar.slider("人氣權重 (Popularity)", 0, 500, 300)
    w_recent = st.sidebar.slider("近況動態 (avg_rank_3)", 0, 500, 250)
    w_weight = st.sidebar.slider("生理數據 (馬體重數值)", 0, 500, 250)
    w_gate = st.sidebar.slider("地理宿命 (檔位變數)", 0, 500, 220)

    # --- 4. 後端 LightGBM 模型訓練 (大數據機器學習基底) ---
    features = ['popularity', 'weight_val', 'avg_rank_3', 'gate', 'career_win_rate', 'weight_carried', 'age', 'sex_code']
    X = df_master[features]
    y = df_master['rank_num']
    
    if HAS_LGB:
        params = {'objective': 'regression', 'metric': 'rmse', 'verbosity': -1, 'seed': 42, 'learning_rate': 0.05}
        train_data = lgb.Dataset(X, label=y)
        lgb_model = lgb.train(params, train_data, num_boost_round=250)
        df_master['lgb_predicted_score'] = lgb_model.predict(X)
    else:
        df_master['lgb_predicted_score'] = df_master['popularity'] * 0.5 + df_master['avg_rank_3'] * 0.5

    # --- 5. 自定義動態評分計算 ---
    df_master['custom_score'] = (
        df_master['popularity'] * (w_pop / 100) +
        df_master['avg_rank_3'] * (w_recent / 100) +
        df_master['gate'] * (w_gate / 100) +
        np.abs(df_master['weight_val'] - df_master['weight_val'].median()) * (w_weight / 500)
    )

    # 篩選當前選擇的年份賽事
    race_mask = (df_master['レース名'].str.contains(r'天皇賞\(秋\)', na=False)) & (df_master['日付'] == target_date)
    race_df = df_master[race_mask].copy()

    # 🚀 升級：清洗多年份重複抓取的馬匹紀錄，確保每匹參賽馬在當屆獨立唯一
    race_df = race_df.drop_duplicates(subset=['horse_name'])

    # 計算當屆內部排名
    race_df['lgb_rank'] = race_df['lgb_predicted_score'].rank(method='min').astype(int)
    race_df['custom_rank'] = race_df['custom_score'].rank(method='min').astype(int)

    # --- 6. 前端 UI 渲染 ---
    st.title("🏆 天皇賞（秋）多歷史維度 AI 預測實驗室")
    st.markdown(f"當前觀測戰局：**{selected_label}** | 官方賽事日期：`{race_description}`")
    st.markdown("賽道特性：**東京競馬場 2000m 左迴旋・直線長 525m・著名的起跑點外檔悲劇**")
    
    if not HAS_LGB:
        st.warning("⚠️ 本地未偵測到 LightGBM 套件，採用基準權重分配進行預測。")

    # 功能分頁
    tab1, tab2, tab3 = st.tabs(["🔮 預測與回測中心", "🧪 動態權重實驗室", "📜 血統與敘事文本"])
    
    with tab1:
        st.subheader("🤖 機器學習模型 (LightGBM) 預測對決實際賽果")
        st.caption("名次越小代表 AI 越看好。請對比『AI 預測名次』與金/銀/銅標註的『實際名次』。")
        
        display_df = race_df.sort_values('lgb_rank').copy()
        display_df['實際名次'] = display_df['rank_num'].astype(int)
        display_df['AI 預測名次'] = display_df['lgb_rank']
        
        # 金銀銅前三名亮點標註
        def highlight_top3(val):
            color = '#FFD700' if val == 1 else '#C0C0C0' if val == 2 else '#CD7F32' if val == 3 else ''
            return f'background-color: {color}; color: black; font-weight: bold;' if color else ''
            
        styled_df = display_df[['AI 預測名次', '實際名次', 'horse_name', 'jockey_name', 'popularity', 'avg_rank_3', 'gate']].style.map(highlight_top3, subset=['實際名次'])
        st.dataframe(styled_df, use_container_width=True)
        
        # 實時命中率統計
        st.markdown("### 🎯 當屆前三名馬匹捕獲觀測")
        col1, col2 = st.columns(2)
        with col1:
            top3_actual = set(display_df.sort_values('實際名次')['horse_name'].head(3))
            top3_pred = set(display_df.sort_values('AI 預測名次')['horse_name'].head(3))
            hit_horses = top3_actual.intersection(top3_pred)
            st.metric(label="成功捕獲當屆前三名數量", value=f"{len(hit_horses)} / 3", delta=f"命中馬匹: {', '.join(hit_horses)}" if hit_horses else "冷門戰局，考驗模型！")
        with col2:
            st.info("💡 **Demo 匯報核心提示：**\n多年份回測能有效幫我們抓出『模型的靈魂』。你可以切換 2024 與 2023 年，觀察模型面對大熱門翻車（如 2024 年 Liberty Island 慘敗）時，AI 是否能保持冷靜，不盲從『人氣』權重。")

    with tab2:
        st.subheader("🧪 現場權重微調動態洗牌")
        st.markdown("調整左側的滑桿，下方的自定義模型會**立刻即時重新排列名次**。可以在報告現場邀請老師出題測試！")
        
        custom_display = race_df.sort_values('custom_rank').copy()
        custom_display['自定義排名'] = custom_display['custom_rank']
        custom_display['實際名次'] = custom_display['rank_num'].astype(int)
        
        st.dataframe(
            custom_display[['自定義排名', '實際名次', 'horse_name', 'popularity', 'avg_rank_3', 'weight_val', 'gate']],
            use_container_width=True
        )
        st.caption("📊 馬匹綜合特徵風險分值分佈圖（分值越低越具冠軍相）：")
        st.bar_chart(data=custom_display.set_index('horse_name')['custom_score'], use_container_width=True)

    with tab3:
        st.subheader("📜 文學視角：血統的文本分析與地理宿命")
        st.markdown("將日本競馬的『血統文本小說』與『賽道宿命』具象化。點開下方各馬匹展開文本拆解：")
        
        for idx, row in race_df.sort_values('rank_num').iterrows():
            with st.expander(f"🐴 {row['horse_name']} (實際名次: {int(row['rank_num'])}着 | {int(row['popularity'])}番人氣)"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(f"**🧬 血統文本**")
                    st.write(f"父系：{row['父系']}")
                    st.write(f"母父系：{row['母父系']}")
                with c2:
                    st.markdown(f"**📍 地理宿命**")
                    st.write(f"所抽檔位：{int(row['gate'])} 檔")
                    if row['gate'] >= 6:
                        st.write("⚠️ *警告：抽到東京2000m大外檔，面臨多跑外疊的地理劣勢。*")
                    else:
                        st.write("✅ *優勢：順利切入內欄經濟線路。*")
                with c3:
                    st.markdown(f"**📈 數據狀態**")
                    st.write(f"馬體重：{row['weight_val']} kg")
                    st.write(f"過去三場均名：{row['avg_rank_3']:.2f}")