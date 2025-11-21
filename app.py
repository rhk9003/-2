import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io

# 設定中文字型 (為了讓雲端環境也能盡量顯示中文)
# 在 Streamlit Cloud 上通常需要額外設定字型，這裡使用通用設定
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'Arial', 'WenQuanYi Zen Hei']
plt.rcParams['axes.unicode_minus'] = False

def analyze_data(df):
    """執行核心分析邏輯"""
    # 1. 資料清理
    if '天數' not in df.columns:
        st.error("錯誤：CSV 中找不到 '天數' 欄位，請確認匯出的報表格式是否正確。")
        return None, None

    df['Date'] = pd.to_datetime(df['天數'])
    
    fill_cols = ['曝光次數', '花費金額 (TWD)', '連結點擊次數', '連結頁面瀏覽次數', 'free course']
    for col in fill_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0)
        else:
            df[col] = 0

    # 2. 每日數據聚合
    daily_stats = df.groupby('Date')[fill_cols].sum().reset_index()

    # 3. 計算進階偵查指標
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
    
    return daily_stats

def plot_charts(plot_data):
    """繪製分析圖表"""
    fig, axes = plt.subplots(3, 1, figsize=(10, 15), sharex=True)
    
    # 圖 1: 流量品質
    ax1 = axes[0]
    ax1.plot(plot_data['Date'], plot_data['連結點擊次數'], label='Clicks', marker='o', color='tab:blue')
    ax1.plot(plot_data['Date'], plot_data['連結頁面瀏覽次數'], label='PVs', linestyle='--', color='tab:green')
    ax1.set_title('Traffic Quality (Gap Check)', fontsize=14)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 圖 2: 頁面轉換率
    ax2 = axes[1]
    ax2.plot(plot_data['Date'], plot_data['Page_CVR'], color='tab:purple', label='Page CVR (%)')
    ax2.set_title('Conversion Trust (Impact of Comments)', fontsize=14)
    ax2.set_ylabel('%')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 圖 3: CPM 成本
    ax3 = axes[2]
    ax3.plot(plot_data['Date'], plot_data['CPM'], color='tab:red', label='CPM')
    ax3.set_title('Cost Penalty Monitor', fontsize=14)
    ax3.set_ylabel('TWD')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    return fig

# --- Streamlit 應用程式介面 ---
st.title("🛡️ 廣告異常流量與詐欺偵測器")
st.markdown("""
請上傳 Facebook 廣告報表 (CSV)，系統將自動檢測：
1. **機器人流量** (異常低的流失率)
2. **惡意留言影響** (轉換率驟降)
3. **演算法懲罰** (CPM 異常上升)
""")

uploaded_file = st.file_uploader("請將 CSV 檔案拖曳至此", type="csv")

if uploaded_file is not None:
    try:
        # 讀取上傳的檔案
        df = pd.read_csv(uploaded_file)
        
        # 執行分析
        daily_stats = analyze_data(df)
        
        if daily_stats is not None:
            st.success("分析完成！以下是檢測結果：")
            
            # 顯示圖表
            # 過濾掉太早期的空值，只畫有數據的區間
            start_date = daily_stats[daily_stats['曝光次數'] > 0]['Date'].min()
            plot_data = daily_stats[daily_stats['Date'] >= start_date]
            
            fig = plot_charts(plot_data)
            st.pyplot(fig)
            
            # 準備下載資料
            # 1. CSV
            csv_buffer = daily_stats.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            
            # 2. 圖片
            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format='png')
            img_buffer.seek(0)
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="📥 下載分析報表 (CSV)",
                    data=csv_buffer,
                    file_name="daily_ads_forensics.csv",
                    mime="text/csv",
                )
            with col2:
                st.download_button(
                    label="🖼️ 下載趨勢圖表 (PNG)",
                    data=img_buffer,
                    file_name="daily_ads_trends.png",
                    mime="image/png",
                )
                
            # 顯示數據預覽
            st.subheader("數據明細預覽")
            st.dataframe(daily_stats.tail(10))
            
    except Exception as e:
        st.error(f"無法處理檔案，請確認格式是否正確。錯誤訊息：{e}")
