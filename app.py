import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import urllib.request

# --- 設定頁面 ---
st.set_page_config(page_title="廣告成效分析", layout="wide")
st.title("📊 每日廣告成效趨勢分析")

# --- 關鍵：解決 Streamlit 中文亂碼問題 ---
# 使用 @st.cache_resource 避免每次重新整理都重複下載
@st.cache_resource
def get_chinese_font():
    # 檢查字型檔是否存在，不存在則下載 (使用 Google Noto Sans TC)
    font_path = "NotoSansCJKtc-Regular.otf"
    url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf"
    
    if not os.path.exists(font_path):
        with st.spinner('正在下載中文字型檔 (首次執行需時約 10-30 秒)...'):
            try:
                urllib.request.urlretrieve(url, font_path)
                st.success("字型下載完成！")
            except Exception as e:
                st.error(f"字型下載失敗，圖表中文可能無法顯示。錯誤: {e}")
                return None
                
    return fm.FontProperties(fname=font_path)

# 取得字型物件
font_prop = get_chinese_font()

# --- 檔案上傳區 ---
uploaded_file = st.file_uploader("請上傳 CSV 報表檔案 (例如: 分析 (1).csv)", type=['csv'])

if uploaded_file is not None:
    # 1. 讀取資料
    try:
        df = pd.read_csv(uploaded_file)
        
        # 2. 資料處理
        metrics_to_fill = ['連結點擊次數', 'free course', '曝光次數', '花費金額 (TWD)']
        for col in metrics_to_fill:
            if col in df.columns:
                df[col] = df[col].fillna(0)
        
        df['天數'] = pd.to_datetime(df['天數'])
        
        # 每日加總
        daily_stats = df.groupby('天數')[['曝光次數', '花費金額 (TWD)', '連結點擊次數', 'free course']].sum().reset_index()
        
        # 計算指標 (KPIs)
        # 避免分母為 0 的安全計算
        daily_stats['CPM'] = daily_stats.apply(lambda x: (x['花費金額 (TWD)'] / x['曝光次數'] * 1000) if x['曝光次數'] > 0 else 0, axis=1)
        daily_stats['CTR'] = daily_stats.apply(lambda x: (x['連結點擊次數'] / x['曝光次數']) if x['曝光次數'] > 0 else 0, axis=1)
        daily_stats['CVR'] = daily_stats.apply(lambda x: (x['free course'] / x['連結點擊次數']) if x['連結點擊次數'] > 0 else 0, axis=1)
        
        # 只顯示有花費的日子
        plot_data = daily_stats[daily_stats['花費金額 (TWD)'] > 0].copy()
        plot_data['日期str'] = plot_data['天數'].dt.strftime('%m-%d')

        # --- 3. 顯示數據表格 ---
        with st.expander("點擊查看詳細數據表格"):
            st.dataframe(plot_data.style.format({
                'CPM': '{:.2f}',
                'CTR': '{:.2%}',
                'CVR': '{:.2%}',
                '花費金額 (TWD)': '{:.0f}'
            }))

        # --- 4. 繪製圖表 (Matplotlib) ---
        st.subheader("趨勢圖表")
        
        metrics_config = [
            ('曝光次數', '每日曝光數 (Impressions)', 'blue'),
            ('花費金額 (TWD)', '每日花費 (Spend)', 'red'),
            ('CPM', 'CPM (每千次曝光成本)', 'purple'),
            ('連結點擊次數', '連結點擊次數 (Link Clicks)', 'green'),
            ('CTR', 'CTR (點擊率)', 'orange'),
            ('free course', 'Free Course 轉換次數', 'brown'),
            ('CVR', '連結點擊-轉換轉換率 (CVR)', 'magenta')
        ]
        
        # 建立畫布 (調整高度以適應網頁)
        fig, axes = plt.subplots(4, 2, figsize=(12, 18))
        axes = axes.flatten()
        
        for i, (col, title, color) in enumerate(metrics_config):
            ax = axes[i]
            ax.plot(plot_data['日期str'], plot_data[col], marker='o', color=color, linewidth=2)
            
            # 套用下載的中文字型
            if font_prop:
                ax.set_title(title, fontproperties=font_prop, fontsize=14)
                ax.set_xlabel('日期', fontproperties=font_prop)
                for label in ax.get_yticklabels() + ax.get_xticklabels():
                    label.set_fontproperties(font_prop)
            else:
                ax.set_title(title) # Fallback
                
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
        
        # 這是 Streamlit 顯示圖表的關鍵指令
        st.pyplot(fig)
        
    except Exception as e:
        st.error(f"處理檔案時發生錯誤: {e}")
else:
    st.info("請上傳 CSV 檔案以開始分析")
