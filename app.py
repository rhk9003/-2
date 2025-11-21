import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import io
import os
import requests

# --- 核心修正：自動下載並設定中文字型 ---
def configure_chinese_font():
    # 字型檔案名稱
    font_filename = "NotoSansTC-Regular.ttf"
    
    # 如果檔案不存在，從 Google Fonts 下載 (使用 Github Raw 連結)
    if not os.path.exists(font_filename):
        with st.spinner("正在下載中文字型檔 (首次執行需時較久)..."):
            try:
                url = "https://github.com/google/fonts/raw/main/ofl/notosanstc/NotoSansTC-Regular.ttf"
                response = requests.get(url)
                with open(font_filename, "wb") as f:
                    f.write(response.content)
                st.success("中文字型下載完成！")
            except Exception as e:
                st.error(f"字型下載失敗，圖表中文可能無法顯示。錯誤：{e}")
                return None

    # 將字型加入 Matplotlib 管理器
    try:
        fm.fontManager.addfont(font_filename)
        plt.rcParams['font.family'] = 'Noto Sans TC'
        return True
    except Exception as e:
        st.warning(f"字型設定失敗：{e}")
        return None

# 執行字型設定
configure_chinese_font()
plt.rcParams['axes.unicode_minus'] = False # 解決負號顯示問題

# --- 以下為分析邏輯 (保持不變) ---

def find_conversion_column(df):
    """智慧偵測轉換欄位名稱 (處理 free course 與 free-course 的差異)"""
    possible_names = ['free course', 'free-course', 'Free Course', 'Free-Course', '成果']
    
    # 1. 優先搜尋名稱完全符合的欄位
    for name in possible_names:
        if name in df.columns:
            return name
            
    # 2. 若找不到，搜尋包含 'free' 和 'course' 的欄位
    for col in df.columns:
        if 'free' in col.lower() and 'course' in col.lower():
            return col
            
    return None

def analyze_data(df):
    """執行核心分析邏輯"""
    if '天數' not in df.columns:
        st.error("錯誤：CSV 中找不到 '天數' 欄位。")
        return None

    df['Date'] = pd.to_datetime(df['天數'])
    
    # 偵測轉換欄位
    conv_col = find_conversion_column(df)
    if conv_col is None:
        st.warning("⚠️ 警告：找不到 'free course' 相關欄位，轉換數將顯示為 0。")
        df['Conversions'] = 0
    else:
        df['Conversions'] = pd.to_numeric(df[conv_col], errors='coerce').fillna(0)

    # 填補與轉換數值
    fill_cols = ['曝光次數', '花費金額 (TWD)', '連結點擊次數', '連結頁面瀏覽次數']
    for col in fill_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0
            
    # 每日數據聚合
    daily_stats = df.groupby('Date').agg({
        '曝光次數': 'sum',
        '花費金額 (TWD)': 'sum',
        '連結點擊次數': 'sum',
        'Conversions': 'sum'
    }).reset_index()

    # 計算關鍵指標
    daily_stats['CPM'] = np.where(daily_stats['曝光次數'] > 0, 
                                  (daily_stats['花費金額 (TWD)'] / daily_stats['曝光次數']) * 1000, 0)
    daily_stats['CTR'] = np.where(daily_stats['曝光次數'] > 0, 
                                  (daily_stats['連結點擊次數'] / daily_stats['曝光次數']) * 100, 0)
    daily_stats['CVR'] = np.where(daily_stats['連結點擊次數'] > 0, 
                                  (daily_stats['Conversions'] / daily_stats['連結點擊次數']) * 100, 0)

    return daily_stats

def plot_charts(plot_data):
    """繪製 7 大關鍵指標波動圖"""
    fig, axes = plt.subplots(7, 1, figsize=(12, 24), sharex=True)
    
    metrics = [
        ('曝光次數', '曝光數 (Impressions)', 'tab:blue'),
        ('花費金額 (TWD)', '花費 (Spend)', 'tab:green'),
        ('CPM', 'CPM (每千次曝光成本)', 'tab:red'),
        ('連結點擊次數', '連結點擊次數 (Link Clicks)', 'tab:orange'),
        ('CTR', '點擊率 CTR (%)', 'tab:purple'),
        ('Conversions', 'free course 轉換次數', 'tab:brown'),
        ('CVR', '連結點擊-轉換轉換率 CVR (%)', 'tab:pink')
    ]

    for ax, (col, title, color) in zip(axes, metrics):
        ax.plot(plot_data['Date'], plot_data[col], marker='.', linestyle='-', color=color, linewidth=1.5)
        ax.set_title(title, fontsize=14, fontweight='bold') # 字型大小調大一點
        ax.grid(True, alpha=0.3)
        
        if not plot_data[col].empty and plot_data[col].max() > 0:
            max_val = plot_data[col].max()
            max_date = plot_data.loc[plot_data[col].idxmax(), 'Date']
            ax.annotate(f'{max_val:.1f}', 
                        xy=(max_date, max_val), 
                        xytext=(10, 5), textcoords='offset points',
                        arrowprops=dict(arrowstyle='->', color='black'))

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    plt.xticks(rotation=45)
    plt.xlabel('日期', fontsize=12)
    plt.tight_layout()
    
    return fig

# --- Streamlit 介面 ---
st.title("📊 廣告成效核心指標看板")
st.markdown("上傳 CSV 後，系統將自動呈現您指定的 7 大指標波動。")

uploaded_file = st.file_uploader("請上傳廣告分析報表 (CSV)", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        daily_stats = analyze_data(df)
        
        if daily_stats is not None:
            st.success("分析完成！")
            
            # 顯示下載按鈕與圖表
            output_cols = {
                'Date': '日期',
                '曝光次數': '曝光數',
                '花費金額 (TWD)': '花費',
                'CPM': 'CPM',
                '連結點擊次數': '點擊次數',
                'CTR': '點擊率(%)',
                'Conversions': 'free course 轉換次數',
                'CVR': '連結點擊-轉換轉換率(%)'
            }
            csv_df = daily_stats.rename(columns=output_cols)
            
            start_date = daily_stats[daily_stats['曝光次數'] > 0]['Date'].min()
            if pd.isna(start_date):
                plot_data = daily_stats
            else:
                plot_data = daily_stats[daily_stats['Date'] >= start_date]

            fig = plot_charts(plot_data)
            st.pyplot(fig)
            
            csv_buffer = csv_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format='png')
            img_buffer.seek(0)
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button("📥 下載報表 (CSV)", csv_buffer, "daily_metrics.csv", "text/csv")
            with col2:
                st.download_button("🖼️ 下載圖表 (PNG)", img_buffer, "daily_charts.png", "image/png")
                
            with st.expander("查看詳細數據"):
                st.dataframe(csv_df)
                
    except Exception as e:
        st.error(f"處理檔案時發生錯誤：{e}")
