import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def analyze_with_forensics(file_path):
    # 1. 讀取資料
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"找不到檔案：{file_path}")
        return

    df['Date'] = pd.to_datetime(df['天數'])
    
    # 填補 NaN 為 0
    fill_cols = ['曝光次數', '花費金額 (TWD)', '連結點擊次數', '連結頁面瀏覽次數', 'free course']
    for col in fill_cols:
        df[col] = df[col].fillna(0)

    # 2. 每日數據聚合
    daily_stats = df.groupby('Date')[fill_cols].sum().reset_index()

    # 3. 計算進階偵查指標
    # (A) 頁面轉換率 (Page CVR): 真正進站後轉換的人，排除誤觸點擊
    # 若數值暴跌 -> 內容有問題 或 有惡意留言
    daily_stats['Page_CVR'] = np.where(
        daily_stats['連結頁面瀏覽次數'] > 0,
        (daily_stats['free course'] / daily_stats['連結頁面瀏覽次數']) * 100,
        0
    )

    # (B) 流量流失率 (Dropoff Rate): 點擊後沒等頁面跑完就走的人
    # 若數值過高 (>40%) -> 網速慢 或 誤觸
    # 若數值過低 (<10%) 且無轉換 -> 可能是機器人
    daily_stats['Dropoff_Rate'] = np.where(
        daily_stats['連結點擊次數'] > 0,
        (daily_stats['連結點擊次數'] - daily_stats['連結頁面瀏覽次數']) / daily_stats['連結點擊次數'] * 100,
        0
    )

    # (C) CPM (成本監測)
    daily_stats['CPM'] = np.where(
        daily_stats['曝光次數'] > 0,
        (daily_stats['花費金額 (TWD)'] / daily_stats['曝光次數']) * 1000,
        0
    )

    # 4. 輸出報表
    output_cols = {
        'Date': '日期',
        '連結點擊次數': '點擊數',
        '連結頁面瀏覽次數': '頁面瀏覽數(PV)',
        'free course': '轉換數',
        'Page_CVR': '頁面轉換率(%)', # 關鍵指標：看信任度
        'Dropoff_Rate': '流量流失率(%)', # 關鍵指標：看機器人/誤觸
        'CPM': 'CPM' # 關鍵指標：看負面回饋懲罰
    }
    
    # 儲存 CSV
    daily_stats.rename(columns=output_cols).to_csv('daily_ads_forensics.csv', index=False, encoding='utf-8-sig')
    print("已輸出進階分析報表：daily_ads_forensics.csv")

    # 5. 繪圖 (略，可參考上方自動生成的圖表)

if __name__ == "__main__":
    analyze_with_forensics('分析 (1).csv')
