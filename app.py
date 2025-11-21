import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import urllib.request

# --- 設定頁面 ---
st.set_page_config(page_title="廣告成效動態分析", layout="wide")
st.title("📊 每日廣告成效趨勢分析 (支援自訂欄位)")

# --- 解決中文字型問題 (快取資源) ---
@st.cache_resource
def get_chinese_font():
    font_path = "NotoSansCJKtc-Regular.otf"
    url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf"
    
    if not os.path.exists(font_path):
        with st.spinner('正在下載中文字型檔 (首次執行需時約 10-30 秒)...'):
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
        
        # --- 關鍵修正：動態欄位選擇區 ---
        st.markdown("### 🛠️ 欄位對應設定")
        st.info("由於不同廣告活動的「轉換事件名稱」可能不同，請在下方確認系統抓取的欄位是否正確。")
        
        col1, col2 = st.columns(2)
        
        # 取得所有數值型欄位，方便使用者選擇
        all_columns = df.columns.tolist()
        
        # 嘗試自動偵測常見的欄位名稱
        # 1. 轉換欄位偵測
        default_conv_index = 0
        possible_conv_names = ['free course', '成果', '購買次數', '潛在客戶', '完成註冊', '轉換次數']
        for name in possible_conv_names:
            if name in all_columns:
                default_conv_index = all_columns.index(name)
                break
        
        with col1:
            # 讓使用者選擇代表「轉換」的欄位
            conversion_col = st.selectbox(
                "🎯 請選擇代表「轉換次數 (Conversions)」的欄位：",
                options=all_columns,
                index=default_conv_index,
                help="選擇這份報表中代表主要成果的欄位，例如 'free course' 或 '購買次數'"
            )

        # 定義標準欄位 (通常 Meta 匯出這些名稱是固定的，但若有變動也可在此擴充)
        impressions_col = '曝光次數'
        spend_col = '花費金額 (TWD)'
        clicks_col = '連結點擊次數'
        
        # 檢查必要欄位是否存在
        required_cols = [impressions_col, spend_col, clicks_col, conversion_col]
        missing_cols = [c for c in required_cols if c not in df.columns]
        
        if missing_cols:
            st.error(f"❌ 錯誤：在檔案中找不到以下欄位：{missing_cols}。請檢查 CSV 檔案或確認欄位名稱。")
        else:
            # --- 2. 資料處理與計算 ---
            
            # 填補空值 (使用使用者選定的 conversion_col)
            metrics_to_fill = [clicks_col, conversion_col, impressions_col, spend_col]
            for col in metrics_to_fill:
                df[col] = df[col].fillna(0)
            
            # 轉換日期格式
            df['天數'] = pd.to_datetime(df['天數'])
            
            # 每日加總
            # 注意：這裡使用 conversion_col 變數
            daily_stats = df.groupby('天數')[[impressions_col, spend_col, clicks_col, conversion_col]].sum().reset_index()
            
            # 計算指標 (KPIs)
            # CPM
            daily_stats['CPM'] = daily_stats.apply(
                lambda x: (x[spend_col] / x[impressions_col] * 1000) if x[impressions_col] > 0 else 0, axis=1
            )
            # CTR (連結點閱率)
            daily_stats['CTR'] = daily_stats.apply(
                lambda x: (x[clicks_col] / x[impressions_col]) if x[impressions_col] > 0 else 0, axis=1
            )
            # CVR (連結點擊轉換率) - 使用 conversion_col
            daily_stats['CVR'] = daily_stats.apply(
                lambda x: (x[conversion_col] / x[clicks_col]) if x[clicks_col] > 0 else 0, axis=1
            )
            
            # 過濾資料：只顯示有花費的日子
            plot_data = daily_stats[daily_stats[spend_col] > 0].copy()
            plot_data['日期str'] = plot_data['天數'].dt.strftime('%m-%d')

            # --- 3. 數據呈現 ---
            
            st.divider() # 分隔線
            st.subheader(f"📈 分析報告：{conversion_col} 與核心指標")

            # 顯示數據表格
            with st.expander("點擊查看詳細數據表格"):
                st.dataframe(plot_data.style.format({
                    'CPM': '{:.2f}',
                    'CTR': '{:.2%}',
                    'CVR': '{:.2%}',
                    spend_col: '{:.0f}',
                    conversion_col: '{:.0f}'
                }))

            # --- 4. 繪製圖表 ---
            # 設定圖表內容
            metrics_config = [
                (impressions_col, '每日曝光數 (Impressions)', 'blue'),
                (spend_col, '每日花費 (Spend)', 'red'),
                ('CPM', 'CPM (每千次曝光成本)', 'purple'),
                (clicks_col, '連結點擊次數 (Link Clicks)', 'green'),
                ('CTR', 'CTR (連結點閱率)', 'orange'),
                (conversion_col, f'轉換次數: {conversion_col}', 'brown'), # 動態標題
                ('CVR', '連結點擊-轉換轉換率 (CVR)', 'magenta')
            ]
            
            fig, axes = plt.subplots(4, 2, figsize=(12, 20))
            axes = axes.flatten()
            
            for i, (col, title, color) in enumerate(metrics_config):
                ax = axes[i]
                ax.plot(plot_data['日期str'], plot_data[col], marker='o', color=color, linewidth=2)
                
                # 設定中文字型
                if font_prop:
                    ax.set_title(title, fontproperties=font_prop, fontsize=14)
                    ax.set_xlabel('日期', fontproperties=font_prop)
                    for label in ax.get_yticklabels() + ax.get_xticklabels():
                        label.set_fontproperties(font_prop)
                else:
                    ax.set_title(title)
                    
                ax.grid(True, linestyle='--', alpha=0.7)
                
                # 標註數據
                for x, y in zip(plot_data['日期str'], plot_data[col]):
                    if col in ['CTR', 'CVR']:
                        label_text = f"{y:.1%}"
                    else:
                        label_text = f"{y:.0f}"
                    ax.annotate(label_text, (x, y), textcoords="offset points", xytext=(0,8), ha='center', fontsize=9)

            # 隱藏多餘子圖
            if len(metrics_config) < len(axes):
                axes[len(metrics_config)].axis('off')
                
            plt.tight_layout()
            st.pyplot(fig)

    except Exception as e:
        st.error(f"處理檔案時發生未預期的錯誤: {e}")
        st.write("建議檢查：CSV 檔案是否為標準 UTF-8 編碼，或欄位名稱是否包含特殊符號。")

else:
    st.info("請上傳 CSV 檔案以開始分析")
