import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import tkinter as tk
from tkinter import filedialog
import os

def select_file():
    """開啟視窗讓使用者選擇 CSV 檔案"""
    root = tk.Tk()
    root.withdraw()  # 隱藏主視窗
    file_path = filedialog.askopenfilename(
        title="請選擇 Facebook 廣告分析報表 (CSV)",
        filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
    )
    return file_path

def analyze_with_forensics():
    # 1. 呼叫檔案選擇視窗
    print("正在開啟檔案選擇視窗，請稍候...")
    file_path = select_file()
    
    if not file_path:
        print("未選擇任何檔案，程式結束。")
        return

    print(f"正在分析檔案：{file_path}")
    
    # 2. 讀取資料
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"讀取檔案失敗：{e}")
        return

    # 3. 資料前處理
    if '天數' not in df.columns:
        print("錯誤：CSV 中找不到 '天數' 欄位，請確認匯出的報表格式是否正確。")
        return

    df['Date'] = pd.to_datetime(df['天數'])
    
    # 填補 NaN 為 0
    fill_cols = ['曝光次數', '花費金額 (TWD)', '連結點擊次數', '連結頁面瀏覽次數', 'free course']
    for col in fill_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0)
        else:
            df[col] = 0

    # 4. 每日數據聚合
    daily_stats = df.groupby('Date')[fill_cols].sum().reset_index()

    # 5. 計算進階偵查指標
    # (A) 頁面轉換率 (Page CVR)
    daily_stats['Page_CVR'] = np.where(
        daily_stats['連結頁面瀏覽次數'] > 0,
        (daily_stats['free course'] / daily_stats['連結頁面瀏覽次數']) * 100,
        0
    )

    # (B) 流量流失率 (Dropoff Rate)
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

    # 6. 輸出 CSV 報表
    output_folder = os.path.dirname(file_path) # 存在跟原始檔案一樣的資料夾
    output_csv_name = os.path.join(output_folder, '廣告分析報告_含異常偵測.csv')
    
    output_cols = {
        'Date': '日期',
        '連結點擊次數': '點擊數',
        '連結頁面瀏覽次數': '頁面瀏覽數(PV)',
        'free course': '轉換數',
        'Page_CVR': '頁面轉換率(%)', 
        'Dropoff_Rate': '流量流失率(%)', 
        'CPM': 'CPM' 
    }
    
    daily_stats.rename(columns=output_cols).to_csv(output_csv_name, index=False, encoding='utf-8-sig')
    print(f"報表已儲存至：{output_csv_name}")

    # 7. 繪製圖表 (包含您的三個假設驗證)
    plt.style.use('ggplot')
    # 處理中文字型 (嘗試自動偵測，若無則使用預設)
    import matplotlib.font_manager as fm
    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'Arial'] 
    plt.rcParams['axes.unicode_minus'] = False # 解決負號顯示問題

    # 過濾掉太早期的空值，只畫有數據的區間
    start_date = daily_stats[daily_stats['曝光次數'] > 0]['Date'].min()
    plot_data = daily_stats[daily_stats['Date'] >= start_date]

    fig, axes = plt.subplots(3, 1, figsize=(12, 18), sharex=True)

    # 圖 1: 流量品質
    ax1 = axes[0]
    ax1.plot(plot_data['Date'], plot_data['連結點擊次數'], label='連結點擊 (Clicks)', marker='o')
    ax1.plot(plot_data['Date'], plot_data['連結頁面瀏覽次數'], label='頁面瀏覽 (PV)', linestyle='--')
    ax1.set_title('流量品質監測 (異常低流失率可能為機器人)', fontsize=14)
    ax1.legend()
    ax1.grid(True)

    # 圖 2: 頁面轉換率
    ax2 = axes[1]
    ax2.plot(plot_data['Date'], plot_data['Page_CVR'], color='purple', label='頁面轉換率 (Page CVR)')
    ax2.set_title('轉換信任度監測 (惡意留言會導致此指標大跌)', fontsize=14)
    ax2.set_ylabel('轉換率 (%)')
    ax2.legend()
    ax2.grid(True)

    # 圖 3: CPM 成本
    ax3 = axes[2]
    ax3.plot(plot_data['Date'], plot_data['CPM'], color='red', label='CPM')
    ax3.set_title('成本懲罰監測 (負面回饋會導致 CPM 上升)', fontsize=14)
    ax3.set_ylabel('CPM (TWD)')
    ax3.legend()
    ax3.grid(True)

    # 設定日期格式
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45)
    
    output_img_name = os.path.join(output_folder, '廣告趨勢圖表_異常偵測.png')
    plt.tight_layout()
    plt.savefig(output_img_name)
    print(f"圖表已儲存至：{output_img_name}")
    print("分析完成！")

if __name__ == "__main__":
    analyze_with_forensics()
