import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import urllib.request

# --- 1. 基礎設定 ---
st.set_page_config(page_title="通用廣告成效分析工具", layout="wide")
st.title("📊 每日廣告成效趨勢分析 (除錯版)")

# --- 2. 解決中文字型 ---
@st.cache_resource
def get_chinese_font():
    font_path = "NotoSansCJKtc-Regular.otf"
    url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf"
    if not os.path.exists(font_path):
        try:
            urllib.request.urlretrieve(url, font_path)
        except:
            return None
    return fm.FontProperties(fname=font_path)

font_prop = get_chinese_font()

# --- 3. 檔案上傳 ---
uploaded_file = st.file_uploader("請上傳 CSV 報表檔案", type=['csv'])

if uploaded_file is not None:
    try:
        # 讀取 CSV
        df = pd.read_csv(uploaded_file)
        all_columns = df.columns.tolist()
        
        # --- [除錯區] 顯示系統讀到的所有欄位 ---
        with st.expander("🔍 點擊這裡檢查：檔案裡到底有哪些欄位？"):
            st.write("系統偵測到的欄位名稱列表：")
            st.code(all_columns)
            
        st.markdown("### 🛠️ 欄位對應設定")
        
        # --- 智慧偵測邏輯 ---
        suggested_index = 0
        for idx, col in enumerate(all_columns):
            c_low = col.lower()
            # 排除成本欄位
            if '成本' in col or 'cost' in c_low: continue
            
            # 尋找關鍵字
            if ('free' in c_low and 'course' in c_low): # 抓 free-course 或 free course
                suggested_index = idx
                break
            if '成果' in col or 'result' in c_low:
                suggested_index = idx
                break
            if '轉換' in col and '次數' in col:
                suggested_index = idx
                break

        c1, c2 = st.columns(2)
        with c1:
            # 這裡的 options 是直接從檔案欄位來的，所以絕不會選到不存在的欄位
            conversion_col = st.selectbox(
                "🎯 請確認「轉換」欄位 (系統已自動偵測)：",
                options=all_columns,
                index=suggested_index
            )
            
        # 防呆：尋找標準欄位
        def safe_find_col(keywords, default_name):
            for col in all_columns:
                if keywords in col: return col
            return None # 找不到就回傳 None

        impressions_col = '曝光次數' if '曝光次數' in all_columns else safe_find_col('曝光', '曝光次數')
        spend_col = '花費金額 (TWD)' if '花費金額 (TWD)' in all_columns else safe_find_col('花費', '花費金額 (TWD)')
        clicks_col = '連結點擊次數' if '連結點擊次數' in all_columns else safe_find_col('連結點擊', '連結點擊次數')

        # --- 4. 數據清洗與計算 (防呆版) ---
        
        # 檢查必要欄位是否都存在
        missing_cols = []
        if not impressions_col: missing_cols.append("曝光次數")
        if not spend_col: missing_cols.append("花費金額")
        if not clicks_col: missing_cols.append("連結點擊次數")
        
        if missing_cols:
            st.error(f"❌ 嚴重錯誤：找不到以下關鍵欄位 {missing_cols}，請檢查 CSV 檔案。")
        else:
            # 安全填補空值 (只填補確實存在的欄位)
            cols_to_clean = [impressions_col, spend_col, clicks_col, conversion_col]
            for col in cols_to_clean:
                if col in df.columns:
                    df[col] = df[col].fillna(0)
            
            df['天數'] = pd.to_datetime(df['天數'])
            
            # 每日加總
            daily = df.groupby('天數')[cols_to_clean].sum().reset_index()
            
            # 計算 KPI
            daily['CPM'] = daily.apply(lambda x: (x[spend_col]/x[impressions_col]*1000) if x[impressions_col]>0 else 0, axis=1)
            daily['CTR'] = daily.apply(lambda x: (x[clicks_col]/x[impressions_col]) if x[impressions_col]>0 else 0, axis=1)
            daily['CVR'] = daily.apply(lambda x: (x[conversion_col]/x[clicks_col]) if x[clicks_col]>0 else 0, axis=1)
            
            # 繪圖數據
            plot_df = daily[daily[spend_col] > 0].copy()
            plot_df['日期str'] = plot_df['天數'].dt.strftime('%m-%d')

            # --- 5. 呈現圖表 ---
            st.divider
