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

# --- 初始化 Session State (確保上傳後資料不會消失) ---
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
    
    # 1. 上傳庫存表
    upload_inv = st.file_uploader("上傳最新庫存 (Excel/CSV)", type=['xlsx', 'csv'], key="upload_inv")
    if upload_inv:
        try:
            if upload_inv.name.endswith('xlsx'):
                st.session_state.df_inv = pd.read_excel(upload_inv)
            else:
                st.session_state.df_inv = pd.read_csv(upload_inv)
            st.success("庫存數據已載入！")
        except Exception as e:
            st.error(f"讀取失敗: {e}")

    # 2. 上傳營業紀錄
    upload_sales = st.file_uploader("上傳歷史營業紀錄", type=['xlsx', 'csv'], key="upload_sales")
    if upload_sales:
        try:
            if upload_sales.name.endswith('xlsx'):
                st.session_state.df_sales = pd.read_excel(upload_sales)
            else:
                st.session_state.df_sales = pd.read_csv(upload_sales)
            st.success("營業紀錄已載入！")
        except Exception as e:
            st.error(f"讀取失敗: {e}")

# --- 主要頁面內容 ---
if st.session_state.df_inv is not None and not st.session_state.df_inv.empty:
    tab1, tab2, tab3 = st.tabs(["📊 庫存分析", "📉 執行作廢", "📜 作廢歷史紀錄"])

    with tab1:
        st.subheader("目前庫存狀態")
        df_inv = st.session_state.df_inv.copy()
        df_sales = st.session_state.df_sales.copy()
        
        # 處理日期格式與計算
        df_inv['有效期限'] = pd.to_datetime(df_inv['有效期限'])
        today = datetime.now()
        
        st.dataframe(df_inv, use_container_width=True)

        expiry_info = []
        suggestions = []
        
        # 去年同期範圍 (計算用)
        last_year_today = today - timedelta(days=365)
        start_date = last_year_today - timedelta(days=15)
        end_date = last_year_today + timedelta(days=15)

        for _, row in df_inv.iterrows():
            name = row['物品名稱']
            qty = row['目前數量']
            
            # 效期檢查
            days_left = (row['有效期限'] - today).days
            if days_left < 0:
                expiry_info.append(f"❌ **{name}**: 已過期 ({row['有效期限'].strftime('%Y-%m-%d')})")
            elif days_left <= 7:
                expiry_info.append(f"⚠️ **{name}**: 快過期 ({max(0, days_left)} 天)")

            # 智慧叫貨建議
            if not df_sales.empty:
                df_sales['日期'] = pd.to_datetime(df_sales['日期'])
                past = df_sales[(df_sales['物品名稱'] == name) & (df_sales['日期'].between(start_date, end_date))]
                avg_daily = past['消耗數量'].mean() if not past.empty else 0
                needed = round(avg_daily * buffer_days)
                if qty < needed:
                    suggestions.append(f"📦 **{name}**: 建議補至 {needed} (目前 {qty})")

        # --- 修正後的顯示區域 ---
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🔔 效期預警")
            if expiry_info:
                for m in expiry_info:
                    st.warning(m)
            else:
                st.write("✅ 效期皆在正常範圍內")
        
        with c2:
            st.markdown("#### 💡 叫貨建議")
            if suggestions:
                for s in suggestions:
                    st.info(s)
            else:
                st.write("✅ 庫存水平充足")

        # LINE 通知
        if st.button("發送手機通知 (LINE)"):
            if line_token:
                full_msg = "\n【效期預警】\n" + "\n".join(expiry_info) if expiry_info else "\n效期正常"
                full_msg += "\n\n【叫貨建議】\n" + "\n".join(suggestions) if suggestions else "\n無需補貨"
                requests.post("https://line.me", 
                              headers={"Authorization": f"Bearer {line_token}"}, 
                              data={"message": full_msg})
                st.success("通知已送出！")
            else:
                st.error("請輸入 LINE Token")

else:
    st.info("💡 尚未讀取到庫存資料。請在側邊欄上傳 Excel/CSV，或檢查 Google Sheets ID 是否正確。")
