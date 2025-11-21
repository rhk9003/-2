import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import urllib.request

# --- 1. 基礎設定 (版本標記 v3.0) ---
st.set_page_config(page_title="廣告成效分析 v3.0", layout="wide")
st.title("📊 每日廣告成效趨勢分析 (v3.0 最終版)")

# --- 2. 解決中文字型 ---
@st.cache_resource
def get_chinese_font():
    font_path = "NotoSansCJKtc-Regular.otf"
    url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf"
    if not os.path.exists(font_path):
        try:
            with st.spinner('正在下載字型檔...'):
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
        
        st.success(f"✅ 檔案讀取成功！系統偵測到 {len(all_columns)} 個欄位。")

        st.markdown("### 🛠️ 1. 欄位對應設定")
        
        # --- 智慧偵測邏輯 ---
        suggested_index = 0
        for idx, col in enumerate(all_columns):
            c_low = col.lower()
            # 排除成本欄位
            if '成本' in col or 'cost' in c_low or 'cpa' in c_low: continue
            
            # 尋找關鍵字 (不分大小寫，不分符號)
            if ('free' in c_low and 'course' in c_low): 
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
            # 這裡的 options 是直接從檔案欄位來的，所以絕對不會報錯
            conversion_col = st.selectbox(
                "🎯 請確認您的「轉換 (Conversion)」欄位：",
                options=all_columns,
                index=suggested_index
            )
            
        # 防呆：尋找標準欄位
        def safe_find_col(keywords, default_name):
            for col in all_columns:
                if keywords in col: return col
            return None

        impressions_col = '曝光次數' if '曝光次數' in all_columns else safe_find_col('曝光', '曝光次數')
        spend_col = '花費金額 (TWD)' if '花費金額 (TWD)' in all_columns else safe_find_col('花費', '花費金額 (TWD)')
        clicks_col = '連結點擊次數' if '連結點擊次數' in all_columns else safe_find_col('連結點擊', '連結點擊次數')

        # --- 4. 數據清洗與計算 ---
        missing_cols = []
        if not impressions_col: missing_cols.append("曝光次數")
        if not spend_col: missing_cols.append("花費金額")
        if not clicks_col: missing_cols.append("連結點擊次數")
        
        if missing_cols:
            st.error(f"❌ 找不到以下關鍵欄位 {missing_cols}，無法繪圖。")
        else:
            # 安全填補空值 (關鍵：這裡只填補存在的欄位，不會去填補 'free course')
            cols_to_clean = [impressions_col, spend_col, clicks_col, conversion_col]
            for col in cols_to_clean:
                df[col] = df[col].fillna(0)
            
            df['天數'] = pd.to_datetime(df['天數'])
            
            # 每日加總 (使用變數 conversion_col)
            daily = df.groupby('天數')[cols_to_clean].sum().reset_index()
            
            # 計算 KPI
            daily['CPM'] = daily.apply(lambda x: (x[spend_col]/x[impressions_col]*1000) if x[impressions_col]>0 else 0, axis=1)
            daily['CTR'] = daily.apply(lambda x: (x[clicks_col]/x[impressions_col]) if x[impressions_col]>0 else 0, axis=1)
            
            # 這裡使用 conversion_col 變數，保證與 selectbox 一致
            daily['CVR'] = daily.apply(lambda x: (x[conversion_col]/x[clicks_col]) if x[clicks_col]>0 else 0, axis=1)
            
            # 繪圖數據
            plot_df = daily[daily[spend_col] > 0].copy()
            plot_df['日期str'] = plot_df['天數'].dt.strftime('%m-%d')

            # --- 5. 呈現圖表 ---
            st.divider()
            st.subheader(f"📈 分析報告：{conversion_col}")
            
            # 數據摘要
            m1, m2, m3 = st.columns(3)
            total_conv = plot_df[conversion_col].sum()
            total_spend = plot_df[spend_col].sum()
            cpa = total_spend / total_conv if total_conv > 0 else 0
            
            m1.metric("總花費", f"${total_spend:,.0f}")
            m2.metric(f"總轉換 ({conversion_col})", f"{total_conv:,.0f}")
            m3.metric("平均轉換成本 (CPA)", f"${cpa:,.0f}")

            # 圖表設定
            metrics = [
                (impressions_col, '曝光數', 'blue'),
                (spend_col, '花費', 'red'),
                ('CPM', 'CPM', 'purple'),
                (clicks_col, '連結點擊數', 'green'),
                ('CTR', 'CTR', 'orange'),
                (conversion_col, f'轉換數 ({conversion_col})', 'brown'),
                ('CVR', '轉換率 (CVR)', 'magenta')
            ]
            
            fig, axes = plt.subplots(4, 2, figsize=(12, 18))
            axes = axes.flatten()
            
            for i, (col, title, color) in enumerate(metrics):
                ax = axes[i]
                ax.plot(plot_df['日期str'], plot_df[col], marker='o', color=color, linewidth=2)
                
                if font_prop:
                    ax.set_title(title, fontproperties=font_prop, fontsize=14)
                    ax.set_xlabel('日期', fontproperties=font_prop)
                    for label in ax.get_xticklabels() + ax.get_yticklabels():
                        label.set_fontproperties(font_prop)
                else:
                    ax.set_title(title)
                
                ax.grid(True, linestyle='--', alpha=0.7)
                
                for x, y in zip(plot_df['日期str'], plot_df[col]):
                    label_txt = f"{y:.1%}" if col in ['CTR', 'CVR'] else f"{y:.0f}"
                    ax.annotate(label_txt, (x, y), textcoords="offset points", xytext=(0,8), ha='center', fontsize=9)

            if len(metrics) < len(axes): axes[len(metrics)].axis('off')
            plt.tight_layout()
            st.pyplot(fig)
            
            with st.expander("查看原始數據"):
                st.dataframe(plot_df)

    except Exception as e:
        st.error(f"發生未預期的錯誤: {e}")
        st.info("請確認上傳的檔案是否為 UTF-8 編碼的 CSV。")
else:
    st.info("請上傳 CSV 檔案。")
