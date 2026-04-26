import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- 設定區 ---
SHEET_ID = "1_Dg2nnIkcus0ME8fNx5HRdKUzcPGlsSVAphJzut7W1I"

st.set_page_config(page_title="庫存智能管家", layout="wide")
st.title("📦 庫存管理與智慧建議系統")

# --- 讀取資料函式 ---
def load_data_from_gs(sheet_name):
    url = f"https://google.com{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    try:
        return pd.read_csv(url)
    except:
        return pd.DataFrame()

# --- 初始化資料 ---
if 'df_inv' not in st.session_state:
    st.session_state.df_inv = load_data_from_gs("庫存表")
if 'df_sales' not in st.session_state:
    st.session_state.df_sales = load_data_from_gs("營業紀錄")

# --- 側邊欄：設定與上傳 ---
with st.sidebar:
    st.header("⚙️ 系統設定")
    line_token = st.text_input("LINE Notify Token", type="password")
    buffer_days = st.slider("建議補貨緩衝天數", 1, 30, 7)
    
    st.divider()
    st.header("📂 批次更新資料")
    
    # 上傳庫存表
    upload_inv = st.file_uploader("上傳最新庫存 (Excel/CSV)", type=['xlsx', 'csv'], key="inv")
    if upload_inv:
        new_inv = pd.read_excel(upload_inv) if upload_inv.name.endswith('xlsx') else pd.read_csv(upload_inv)
        if st.button("更新目前庫存數據"):
            st.session_state.df_inv = new_inv
            st.success("庫存數據已暫時更新！")

    # 上傳營業紀錄
    upload_sales = st.file_uploader("上傳歷史營業紀錄", type=['xlsx', 'csv'], key="sales")
    if upload_sales:
        new_sales = pd.read_excel(upload_sales) if upload_sales.name.endswith('xlsx') else pd.read_csv(upload_sales)
        if st.button("更新營業紀錄數據"):
            st.session_state.df_sales = new_sales
            st.success("營業紀錄已暫時更新！")

# --- 主要頁面內容 ---
if not st.session_state.df_inv.empty:
    tab1, tab2, tab3 = st.tabs(["📊 庫存分析", "📉 執行作廢", "📜 作廢歷史紀錄"])

    with tab1:
        st.subheader("目前庫存狀態")
        df_inv = st.session_state.df_inv.copy()
        df_sales = st.session_state.df_sales.copy()
        
        # 確保日期格式
        df_inv['有效期限'] = pd.to_datetime(df_inv['有效期限'])
        today = datetime.now()
        
        st.dataframe(df_inv, use_container_width=True)

        expiry_info = []
        suggestions = []
        
        # 去年同期邏輯
        last_year_today = today - timedelta(days=365)
        start_date = last_year_today - timedelta(days=15)
        end_date = last_year_today + timedelta(days=15)

        for _, row in df_inv.iterrows():
            name, qty = row['物品名稱'], row['目前數量']
            days_left = (row['有效期限'] - today).days
            
            if days_left < 0:
                expiry_info.append(f"❌ **{name}**: 已過期 ({row['有效期限'].strftime('%Y-%m-%d')})")
            elif days_left <= 7:
                expiry_info.append(f"⚠️ **{name}**: 快過期 ({max(0, days_left)} 天)")

            # 智慧建議
            if not df_sales.empty:
                df_sales['日期'] = pd.to_datetime(df_sales['日期'])
                past = df_sales[(df_sales['物品名稱'] == name) & (df_sales['日期'].between(start_date, end_date))]
                avg_daily = past['消耗數量'].mean() if not past.empty else 0
                needed = round(avg_daily * buffer_days)
                if qty < needed:
                    suggestions.append(f"📦 **{name}**: 建議補至 {needed} (目前 {qty})")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🔔 效期預警")
            for m in expiry_info: st.warning(m) if expiry_info else st.write("✅ 正常")
        with c2:
            st.markdown("#### 💡 叫貨建議")
            for s in suggestions: st.info(s) if suggestions else st.write("✅ 充足")

        if st.button("發送手機通知 (LINE)"):
            if line_token:
                msg = "\n" + "\n".join(expiry_info + suggestions)
                requests.post("https://line.me", headers={"Authorization": f"Bearer {line_token}"}, data={"message": msg})
                st.success("通知已送出！")

    with tab2:
        st.write("作廢功能開發中... (與前一版邏輯相同)")
        
else:
    st.info("💡 請先在側邊欄上傳資料，或確認 Google Sheets ID 是否正確。")
