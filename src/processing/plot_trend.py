import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# --- 1. 讀取資料 ---
current_path = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.abspath(os.path.join(current_path, "../../data/raw/tenno_sho_10_years.csv"))

print(f"📦 正在讀取資料: {csv_path}")
df = pd.read_csv(csv_path)

# --- 2. 資料清洗與過濾 ---
# 只篩選出每年「著順」為 1 (第一名) 的資料
df_winner = df[df['着順'].astype(str) == '1'].copy()

# 確保「年度」和「タイム(秒)」為可計算的數值型態
df_winner['年度'] = pd.to_numeric(df_winner['年度'])
df_winner['タイム(秒)'] = pd.to_numeric(df_winner['タイム(秒)'])

# 依據年度排序
df_winner = df_winner.sort_values('年度')

# --- 3. 設定視覺化字體 (解決 Matplotlib 中日文顯示問題) ---
# 自動兼容 Windows 與 Mac 的內建中文字體
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Arial Unicode MS', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

# --- 4. 繪製圖表 ---
plt.figure(figsize=(11, 6))

# 使用 Seaborn 繪製散佈圖與線性回歸趨勢線 (紅色的虛線)
sns.regplot(
    data=df_winner, 
    x='年度', 
    y='タイム(秒)', 
    scatter_kws={'s': 120, 'color': '#1f77b4', 'edgecolor': 'white'}, 
    line_kws={'color': '#d62728', 'linestyle': '--', 'label': '完賽時間趨勢線'}
)

# 在每個資料點旁邊標上「馬名」與「原始時間 (分:秒)」
for i in range(len(df_winner)):
    row = df_winner.iloc[i]
    plt.text(
        row['年度'], 
        row['タイム(秒)'] + 0.15,  # 稍微往下偏移一點避免重疊 (因為秒數大在上方)
        f"{row['馬名']}\n({row['タイム']})", 
        fontsize=9, 
        ha='center',
        bbox=dict(facecolor='white', alpha=0.5, edgecolor='none', pad=1)
    )

plt.title('過去10年 天皇賞(秋) 冠軍完賽時間趨勢 (2015-2024)', fontsize=16, fontweight='bold')
plt.xlabel('年度', fontsize=12)
plt.ylabel('完賽時間 (秒)', fontsize=12)

# 讓 X 軸只顯示整數年份
plt.xticks(df_winner['年度'])

# 加上格線方便對齊
plt.grid(True, linestyle=':', alpha=0.6)
plt.legend(loc='upper right')
plt.tight_layout()

# --- 5. 存檔與顯示 ---
save_dir = os.path.abspath(os.path.join(current_path, "../../data/processed"))
os.makedirs(save_dir, exist_ok=True)
save_path = os.path.join(save_dir, "winning_time_trend.png")

plt.savefig(save_path, dpi=300)
print(f"✨ 趨勢圖已儲存至: {save_path}")

# 直接彈出視窗顯示圖表
plt.show()