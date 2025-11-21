import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import urllib.request
import os

def plot_ads_performance(file_path):
    # --- 第一步：解決中文字型問題 (關鍵) ---
    # 檢查是否有中文字型，若無則自動下載 Noto Sans TC
    font_path = "NotoSansCJKtc-Regular.otf"
    url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf"
    
    if not os.path.exists(font_path):
        print("正在下載中文字型，請稍候...")
        try:
            urllib.request.urlretrieve(url, font_path)
            print("字型下載完成。")
        except Exception as e:
            print(f"字型下載失敗，將使用系統預設字型 (中文可能無法顯示): {e}")
            font_path = None

    # 設定字型屬性
    if font_path and os.path.exists(font_path):
        font_prop = fm.FontProperties(fname=font_path)
    else:
        font_prop = None # fallback

    # --- 第二步：讀取與處理數據 ---
    df = pd.read_csv(file_path)
    
    # 填補空值
    metrics_to_fill = ['連結點擊次數', 'free course', '曝光次數', '花費金額 (TWD)']
    for col in metrics_to_fill:
        if col in df.columns:
            df[col] = df[col].fillna(0)
            
    df['天數'] = pd.to_datetime(df['天數'])
    
    # 每日加總
    daily_stats = df.groupby('天數')[['曝光次數', '花費金額 (TWD)', '連結點擊次數', 'free course']].sum().reset_index()
    
    # 計算關鍵指標 (KPIs)
    daily_stats['CPM'] = (daily_stats['花費金額 (TWD)'] / daily_stats['曝光次數']) * 1000
    daily_stats['CTR'] = daily_stats['連結點擊次數'] / daily_stats['曝光次數']
    daily_stats['CVR'] = daily_stats['free course'] / daily_stats['連結點擊次數'] # 連結點擊-轉換轉換率
    daily_stats = daily_stats.fillna(0)

    # 過濾掉早期無數據的日期 (例如只看最近有數據的區間)
    # 這裡自動偵測：只顯示「花費 > 0」的日期，避免圖表前面有一大段空白
    plot_data = daily_stats[daily_stats['花費金額 (TWD)'] > 0].copy()
    plot_data['日期str'] = plot_data['天數'].dt.strftime('%m-%d')

    # --- 第三步：繪製圖表 ---
    # 建立 4x2 的圖表矩陣
    fig, axes = plt.subplots(4, 2, figsize=(15, 20))
    axes = axes.flatten()
    
    metrics_config = [
        ('曝光次數', '每日曝光數 (Impressions)', 'blue'),
        ('花費金額 (TWD)', '每日花費 (Spend)', 'red'),
        ('CPM', 'CPM (每千次曝光成本)', 'purple'),
        ('連結點擊次數', '連結點擊次數 (Link Clicks)', 'green'),
        ('CTR', 'CTR (點擊率)', 'orange'),
        ('free course', 'Free Course 轉換次數', 'brown'),
        ('CVR', '連結點擊-轉換轉換率 (CVR)', 'magenta')
    ]

    for i, (col, title, color) in enumerate(metrics_config):
        ax = axes[i]
        ax.plot(plot_data['日期str'], plot_data[col], marker='o', color=color, linewidth=2)
        
        # 應用中文字型
        if font_prop:
            ax.set_title(title, fontproperties=font_prop, fontsize=14)
            ax.set_xlabel('日期', fontproperties=font_prop)
            for label in ax.get_yticklabels() + ax.get_xticklabels():
                label.set_fontproperties(font_prop)
        else:
            ax.set_title(title, fontsize=14)
            
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # 加上數據標籤
        for x, y in zip(plot_data['日期str'], plot_data[col]):
            if col in ['CTR', 'CVR']:
                label = f"{y:.1%}"
            else:
                label = f"{y:.0f}"
            ax.annotate(label, (x, y), textcoords="offset points", xytext=(0,10), ha='center', fontsize=10)

    # 隱藏最後一個多餘的子圖
    if len(metrics_config) < len(axes):
        axes[len(metrics_config)].axis('off')

    plt.tight_layout()
    plt.show()

# 執行函式 (請確保 CSV 檔案在同一個資料夾)
plot_ads_performance('分析 (1).csv')
