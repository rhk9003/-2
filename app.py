import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import urllib.request
import re

# --- 設定頁面 ---
st.set_page_config(page_title="全能廣告成效分析", layout="wide")
st.title("📊 每日廣告成效趨勢分析 (支援多版本欄位)")

# --- 解決中文字型問題 ---
@st.cache_resource
def get_chinese_font():
    font_path = "NotoSansCJKtc-Regular.otf"
    url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf"
    
    if not os.path.exists(font_path):
        with st.spinner('正在配置中文字型...'):
            try:
                urllib.request.urlretrieve(url, font_path)
            except Exception as e:
                st.error(f"字型下載失敗: {e}")
                return None
    return fm.FontProperties(fname=font_path)

font_prop = get_chinese_font()

# --- 檔案上傳區 ---
uploaded_file = st.file_uploader("請上傳 CSV 報表檔案", type=['csv'])

if uploaded_file is not None:
    try:
        # 1. 讀取資料
        df = pd.read_csv(uploaded_file)
        
        st.markdown("### 🛠️ 欄位智慧對應")
        
        all_columns = df.columns.tolist()
        
        # --- 智慧偵測邏輯 (核心修正) ---
        # 自動尋找最像「轉換」的欄位
        # 優先順序：包含 'free'且包含'course' -> 包含 '成果'且不含'成本' -> 包含 '轉換'
        suggested_index = 0
        
        for idx, col in enumerate(all_columns):
            col_lower = col.lower()
            # 排除掉 "成本" (Cost) 相關的欄位，只找次數
            if '成本' in col or 'cost' in col_lower or 'cpa' in col_lower or 'cpm' in col_lower:
                continue
                
            # 規則 1: 同時包含 free 和 course (無論中間是空白還是連字號)
            if 'free' in col_lower and 'course' in col_lower:
                suggested_index = idx
                break
            # 規則 2: 叫做 "成果" 或 "results"
            elif col == '成果' or col_lower == 'results':
                suggested_index = idx
                break
            # 規則 3: 包含 "轉換"
            elif '轉換次數' in col:
                suggested_index = idx
                break

        col1, col2 = st.columns(2)
        with col1:
            # 讓使用者確認或修改
            conversion_col = st.selectbox(
                "🎯 系統偵測到您的轉換欄位是 (可手動修改)：",
                options=all_columns,
                index=suggested_index,
                help="請確認這是您要分析的主要成果欄位 (如 free-course, 購買次數等)"
            )

        # 定義其他標準欄位 (通常較固定)
        impressions_col = '曝光次數'
        spend_col = '花費金額 (TWD)'
        clicks_col = '連結點擊次數'
        
        # 檢查必要欄位
        required_cols = [impressions_col, spend_col, clicks_col]
        missing_cols = [c for c in required_cols if c not in df.columns]
        
        if missing_cols:
            st.error(f"⚠️ 檔案格式異常：找不到以下欄位 {missing_cols}。請確認這是否為 Meta 廣告匯出的標準報表。")
        else:
            # --- 2. 資料處理 ---
            # 填補空值
            metrics_to_fill = [clicks_col, conversion_col, impressions_col, spend_col]
            for col in metrics_to_fill:
                if col in df.columns:
                    df[col] = df[col].fillna(0)
            
            # 處理日期
            df['天數'] = pd.to_datetime(df['天數'])
            
            # 每日加總
            daily_stats = df.groupby('天數')[[impressions_col, spend_col, clicks_col, conversion_col]].sum().reset_index()
            
            # 計算指標
            daily_stats['CPM'] = daily_stats.apply(lambda x: (x[spend_col] / x[impressions_col] * 1000) if x[impressions_col] > 0 else 0, axis=1)
            daily_stats['CTR'] = daily_stats.apply(lambda x: (x[clicks_col] / x[impressions_col]) if x[impressions_col] > 0 else 0, axis=1)
            daily_stats['CVR'] = daily_stats.apply(lambda x: (x[conversion_col] / x[clicks_col]) if x[clicks_col] > 0 else 0, axis=1) # 連結點擊轉換率
            
            # 篩選有數據的日期
            plot_data = daily_stats[daily_stats[spend_col] > 0].copy()
            plot_data['日期str'] = plot_data['天數'].dt.strftime('%m-%d')

            # --- 3. 顯示數據與圖表 ---
            st.divider()
            
            # 數據摘要
            total_spend = plot_data[spend_col].sum()
            total_conv = plot_data[conversion_col].sum()
            avg_cpa = total_spend / total_conv if total_conv > 0 else 0
            
            m1, m2, m3 = st.columns(3)
            m1.metric("總花費", f"${total_spend:,.0f}")
            m2.metric(f"總轉換數 ({conversion_col})", f"{total_conv:,.0f}")
            m3.metric("平均轉換成本 (CPA)", f"${avg_cpa:,.0f}")

            # 圖表區
            st.subheader("趨勢圖表")
            
            metrics_config = [
                (impressions_col, '每日曝光數 (Impressions)', 'blue'),
                (spend_col, '每日花費 (Spend)', 'red'),
                ('CPM', 'CPM (每千次曝光成本)', 'purple'),
                (clicks_col, '連結點擊次數 (Link Clicks)', 'green'),
                ('CTR', 'CTR (連結點閱率)', 'orange'),
                (conversion_col, f'轉換次數 ({conversion_col})', 'brown'),
                ('CVR', '連結點擊-轉換轉換率 (CVR)', 'magenta')
            ]
            
            fig, axes = plt.subplots(4, 2, figsize=(12, 20))
            axes = axes.flatten()
            
            for i, (col, title, color) in enumerate(metrics_config):
                ax = axes[i]
                ax.plot(plot_data['日期str'], plot_data[col], marker='o', color=color, linewidth=2)
                
                if font_prop:
                    ax.set_title(title
