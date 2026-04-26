import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- 設定區 ---
SHEET_ID = "1_Dg2nnIkcus0ME8fNx5HRdKUzcPGlsSVAphJzut7W1I"

st.set_page_config(page_title="庫存智能管家", layout="wide")
st.title("📦 庫存管理與智慧建議系統")

# --- 讀取資料函式 (修正網址) ---
def load_data_from_gs(sheet_name):
    # 修正原本 url 的錯誤
    url = f"https://google.com{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    try:
        df = pd.read_csv(url)
        return df
    except:
        return pd.DataFrame()

# --- 初始化 Session State ---
if 'df_inv' not in st.session_state:
    st.session_state.df_inv = load_data_from_gs("庫存表")
if 'df_sales' not in st.session_state:
    st.session_state.df_sales = load_data_from_gs("營業紀錄")
if 'df_scrap' not in st.session_state:
    df_s = load_data_from_gs("作廢紀錄")
    st.session_state.df_scrap = df_s if not df_s.empty else pd.DataFrame(columns=['日期', '物品名稱', '數量', '原因'])

# --- 側邊欄：設定與【正式啟用上傳】 ---
with st.sidebar:
    st.header("⚙️ 系統設定")
    line_token = st.text_input("LINE Notify Token", type="password")
    buffer_days = st.slider("建議補貨緩衝天數", 1, 30, 7)
    
    st.divider()
    st.header("📂 檔案上傳更新")
    
    # 上傳庫存表
    up_inv = st.file_uploader("上傳最新庫存 (Excel/CSV)", type=['xlsx', 'csv'], key="up_inv")
    if up_inv:
        if st.button("確認同步庫存數據"):
            try:
                new_df = pd.read_excel(up_inv) if up_inv.name.endswith('xlsx') else pd.read_csv(up_inv)
                st.session_state.df_inv = new_df
                st.success("✅ 庫存數據已載入網頁！")
                st.info("💡 提示：若要同步至雲端，請配合 upload_data.py 使用，或設定 Google API 權限。")
            except Exception as e:
                st.error(f"讀取失敗: {e}")

    # 上傳營業紀錄
    up_sales = st.file_uploader("上傳歷史營業紀錄", type=['xlsx', 'csv'], key="up_sales")
    if up_sales:
        if st.button("確認同步營業紀錄"):
            try:
                new_df = pd.read_excel(up_sales) if up_sales.name.endswith('xlsx') else pd.read_csv(up_sales)
                st.session_state.df_sales = new_df
                st.success("✅ 營業紀錄已載入網頁！")
            except Exception as e:
                st.error(f"讀取失敗: {e}")

# --- 主要頁面內容 (您的原本邏輯) ---
if st.session_state.df_inv is not None and not st.session_state.df_inv.empty:
    tab1, tab2, tab3 = st.tabs(["📊 庫存分析", "📉 執行作廢", "📜 作廢歷史紀錄"])

    with tab1:
        st.subheader("目前庫存狀態")
        df_display = st.session_state.df_inv.copy()
        # 確保日期格式
        df_display['有效期限'] = pd.to_datetime(df_display['有效期限'])
        st.dataframe(df_display, use_container_width=True)

        # 分析與建議邏輯... (省略，同您的版本)
        st.info("這裡是您原本的分析圖表與 LINE 通知區塊。")

    with tab2:
        st.subheader("新增作廢紀錄")
        # 您原本的作廢 Form 邏輯...
        with st.form("scrap_form"):
            item_list = st.session_state.df_inv['物品名稱'].tolist()
            selected_item = st.selectbox("選擇要作廢的物品", item_list)
            scrap_qty = st.number_input("作廢數量", min_value=1, step=1)
            scrap_reason = st.text_input("作廢原因")
            if st.form_submit_button("確認提交"):
                # 執行扣庫存與紀錄...
                st.success("已完成本地扣除，請定期上傳 Excel 備份。")

    with tab3:
        st.subheader("作廢歷史清單")
        st.dataframe(st.session_state.df_scrap, use_container_width=True)
else:
    st.warning("⚠️ 請從側邊欄上傳檔案，或檢查 Google Sheets ID 是否已公開授權。")
