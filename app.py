import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import urllib.request

# --- 1. 基礎設定 ---
st.set_page_config(page_title="通用廣告成效分析工具", layout="wide")
st.title("📊 每日廣告成效趨勢分析 (通用版)")

# --- 2. 解決中文字型 (Streamlit Cloud 專用) ---
@st.cache_resource
def get_chinese_font():
    # 下載 Google Noto Sans TC 字型
    font_path = "NotoSansCJKtc-Regular.otf"
    url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf"
    
    if not os.path.exists(font_path):
        with st.spinner('正在配置中文字型環境...'):
            try:
                urllib.request.urlretrieve(url, font_path)
            except Exception as e:
                st.error(f"字型下載失敗: {e}")
                return None
    return fm.FontProperties(fname=font_path)

font_prop = get_chinese_font()

# --- 3. 檔案上傳與處理 ---
uploaded_file = st.file_uploader("請上傳 CSV 報表檔案 (支援不同轉換欄位名稱)", type=['csv'])

if uploaded_file is not None:
    try:
        # 讀取 CSV
        df = pd.read_csv(uploaded_file)
        all_columns = df.columns.tolist()
        
        st.markdown("### 🛠️ 欄位對應設定")
        st.info("系統已讀取檔案欄位，請確認下方對應是否正確，特別是「轉換」欄位。")
        
        c1, c2 = st.columns(2)
        
        # --- 智慧偵測轉換欄位 ---
        # 邏輯：尋找包含 'free', 'course', '成果', 'result', '購買' 等關鍵字的欄位
        suggested_index = 0
        for idx, col in enumerate(all_columns):
            c_low = col.lower()
            # 排除成本欄位 (例如 "每個 free course 的成本")
            if '成本' in col or 'cost' in c_low or 'cpa' in c_low or 'cpm' in c_low:
                continue
            
            # 優先順序判定
            if ('free' in c_low and 'course' in c_low): # 抓 free course 或 free-course
                suggested_index = idx
                break
            if col == '成果' or c_low == 'results':
                suggested_index = idx
                break
            if '購買' in col and '次數' in col:
                suggested_index = idx
                break
            if '轉換' in col and '次數' in col:
                suggested_index = idx
                break

        # 讓使用者選擇欄位 (預設為偵測到的欄位)
        with c1:
            conversion_col = st.selectbox(
                "🎯 請選擇代表「轉換次數」的欄位：",
                options=all_columns,
                index=suggested_index,
                help="不同報表的轉換名稱可能不同 (如 free-course, free course, 購買次數)"
            )
            
        # 其他關鍵欄位 (通常名稱較固定，但若有變動可在此修改)
        # 這裡做簡單的防呆，如果找不到標準名稱，嘗試找類似的
        def find_col(keywords, default):
            for col in all_columns:
                if keywords in col:
                    return col
            return default

        impressions_col = '曝光次數' if '曝光次數' in all_columns else find_col('曝光', '曝光次數')
        spend_col = '花費金額 (TWD)' if '花費金額 (TWD)' in all_columns else find_col('花費', '花費金額 (TWD)')
        clicks_col = '連結點擊次數' if '連結點擊次數' in all_columns else find_col('連結點擊', '連結點擊次數')

        # 檢查是否缺少必要欄位
        missing = [c for c in [impressions_col, spend_col, clicks_col] if c not in df.columns]
        
        if missing:
            st.error(f"❌ 找不到必要欄位: {missing}。請檢查 CSV 檔案。")
        else:
            # --- 4. 數據清洗與計算 ---
            
            # 使用變數 (conversion_col) 而非字串，確保不會報錯
            cols_to_clean = [impressions_col, spend_col, clicks_col, conversion_col]
            for col in cols_to_clean:
                df[col] = df[col].fillna(0)
            
            df['天數'] = pd.to_datetime(df['天數'])
            
            # 每日加總
            daily = df.groupby('天數')[cols_to_clean].sum().reset_index()
            
            # 計算 KPI (防呆除以0)
            daily['CPM'] = daily.apply(lambda x: (x[spend_col]/x[impressions_col]*1000) if x[impressions_col]>0 else 0, axis=1)
            daily['CTR'] = daily.apply(lambda x: (x[clicks_col]/x[impressions_col]) if x[impressions_col]>0 else 0, axis=1)
            
            # 關鍵：使用選定的 conversion_col 計算 CVR
            daily['CVR'] = daily.apply(lambda x: (x[conversion_col]/x[clicks_col]) if x[clicks_col]>0 else 0, axis=1)
            
            # 只取有花費的日子來畫圖
            plot_df = daily[daily[spend_col] > 0].copy()
            plot_df['日期str'] = plot_df['天數'].dt.strftime('%m-%d')

            # --- 5. 呈現圖表 ---
            st.divider()
            st.subheader(f"📈 分析目標：{conversion_col}")
            
            # 顯示摘要數據
            col1, col2, col3 = st.columns(3)
            col1.metric("總花費", f"${plot_df[spend_col].sum():,.0f}")
            col2.metric("總轉換數", f"{plot_df[conversion_col].sum():,.0f}")
            
            avg_cpa = plot_df[spend_col].sum() / plot_df[conversion_col].sum() if plot_df[conversion_col].sum() > 0 else 0
            col3.metric("平均成本 (CPA)", f"${avg_cpa:,.0f}")

            # 設定圖表參數
            metrics = [
                (impressions_col, '曝光數', 'blue'),
                (spend_col, '花費 (TWD)', 'red'),
                ('CPM', 'CPM', 'purple'),
                (clicks_col, '連結點擊數', 'green'),
                ('CTR', 'CTR (點擊率)', 'orange'),
                (conversion_col, f'轉換數 ({conversion_col})', 'brown'), # 動態標題
                ('CVR', '轉換率 (CVR)', 'magenta')
            ]
            
            # 繪圖
            fig, axes = plt.subplots(4, 2, figsize=(12, 18))
            axes = axes.flatten()
            
            for i, (col, title, color) in enumerate(metrics):
                ax = axes[i]
                ax.plot(plot_df['日期str'], plot_df[col], marker='o', color=color, linewidth=2)
                
                if font_prop:
                    ax.set_title(title, fontproperties=font_prop, fontsize=14)
                    ax.set_xlabel('日期', fontproperties=font_prop)
                    # 設定軸刻度字型
                    for label in ax.get_xticklabels() + ax.get_yticklabels():
                        label.set_fontproperties(font_prop)
                else:
                    ax.set_title(title)
                
                ax.grid(True, linestyle='--', alpha=0.7)
                
                # 標籤數值
                for x, y in zip(plot_df['日期str'], plot_df[col]):
                    label_txt = f"{y:.1%}" if col in ['CTR', 'CVR'] else f"{y:.0f}"
                    ax.annotate(label_txt, (x, y), textcoords="offset points", xytext=(0,8), ha='center', fontsize=9)

            # 關閉多餘子圖
            if len(metrics) < len(axes):
                axes[len(metrics)].axis('off')
                
            plt.tight_layout()
            st.pyplot(fig)
            
            with st.expander("查看原始數據"):
                st.dataframe(plot_df)

    except Exception as e:
        st.error(f"處理檔案時發生錯誤: {e}")
        st.write("建議：請檢查上傳的 CSV 是否為 UTF-8 編碼，並確認包含必要的數據欄位。")

else:
    st.info("👋 請上傳 CSV 檔案。系統會自動偵測並讓您選擇正確的轉換欄位。")
