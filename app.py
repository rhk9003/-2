import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def analyze_ads_data(file_path):
    # 1. 讀取資料
    try:
        df = pd.read_csv(file_path)
        print("檔案讀取成功。")
    except FileNotFoundError:
        print(f"找不到檔案：{file_path}")
        return

    # 2. 資料清理與前處理
    # 轉換日期格式
    if '天數' in df.columns:
        df['Date'] = pd.to_datetime(df['天數'])
    else:
        print("錯誤：找不到 '天數' 欄位")
        return

    # 填補缺失值 (將 NaN 補為 0 以便計算總和)
    fill_cols = ['曝光次數', '花費金額 (TWD)', '連結點擊次數', 'free course']
    for col in fill_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0)
        else:
            print(f"警告：找不到 '{col}' 欄位，將視為 0")
            df[col] = 0

    # 3. 依日期加總資料 (Aggregation)
    daily_df = df.groupby('Date')[fill_cols].sum().reset_index()

    # 4. 計算衍生指標 (避免除以零的錯誤)
    # CPM = (花費 / 曝光) * 1000
    daily_df['CPM'] = np.where(daily_df['曝光次數'] > 0, 
                               (daily_df['花費金額 (TWD)'] / daily_df['曝光次數']) * 1000, 0)

    # CTR = (連結點擊 / 曝光) * 100
    daily_df['CTR'] = np.where(daily_df['曝光次數'] > 0, 
                               (daily_df['連結點擊次數'] / daily_df['曝光次數']) * 100, 0)

    # CVR = (轉換 / 連結點擊) * 100 (連結點擊-轉換轉換率)
    daily_df['CVR'] = np.where(daily_df['連結點擊次數'] > 0, 
                               (daily_df['free course'] / daily_df['連結點擊次數']) * 100, 0)

    # 依日期排序
    daily_df = daily_df.sort_values('Date')

    # 5. 輸出 CSV 報表
    output_cols = {
        'Date': '日期',
        '曝光次數': '曝光數',
        '花費金額 (TWD)': '花費',
        'CPM': 'CPM',
        '連結點擊次數': '連結點擊次數',
        'CTR': '點擊率(%)',
        'free course': 'free course 轉換次數',
        'CVR': '連結點擊-轉換轉換率(%)'
    }
    csv_output = daily_df.rename(columns=output_cols)
    csv_output.to_csv('daily_ads_analysis.csv', index=False, encoding='utf-8-sig')
    print("已輸出報表：daily_ads_analysis.csv")

    # 6. 繪製趨勢圖
    # 過濾掉前面完全沒有曝光的日子，讓圖表更聚焦
    start_date = daily_df[daily_df['曝光次數'] > 0]['Date'].min()
    if pd.notna(start_date):
        plot_df = daily_df[daily_df['Date'] >= start_date]
    else:
        plot_df = daily_df

    # 設定繪圖風格
    plt.style.use('ggplot')
    fig, axes = plt.subplots(7, 1, figsize=(12, 20), sharex=True)

    # 定義圖表內容
    metrics = [
        ('曝光次數', 'Impressions (曝光數)', 'tab:blue'),
        ('花費金額 (TWD)', 'Spend (花費)', 'tab:green'),
        ('CPM', 'CPM', 'tab:red'),
        ('連結點擊次數', 'Link Clicks (連結點擊)', 'tab:orange'),
        ('CTR', 'CTR (點擊率 %)', 'tab:purple'),
        ('free course', 'Conversions (轉換數)', 'tab:brown'),
        ('CVR', 'CVR (連結點擊轉換率 %)', 'tab:pink')
    ]

    for ax, (col, title, color) in zip(axes, metrics):
        ax.plot(plot_df['Date'], plot_df[col], marker='.', linestyle='-', color=color, linewidth=1.5)
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # 標註最大值
        if not plot_df[col].empty:
            max_val = plot_df[col].max()
            max_date = plot_df.loc[plot_df[col].idxmax(), 'Date']
            ax.annotate(f'Max: {max_val:.1f}', 
                        xy=(max_date, max_val), 
                        xytext=(10, 10), textcoords='offset points',
                        arrowprops=dict(arrowstyle='->', color='black'))

    # 設定 X 軸日期格式
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    plt.savefig('daily_ads_trends.png')
    print("已輸出圖表：daily_ads_trends.png")

# 執行主程式
if __name__ == "__main__":
    analyze_ads_data('分析 (1).csv')
