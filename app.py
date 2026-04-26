import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime, timedelta

# --- 設定區 ---
SHEET_ID = "1_Dg2nnIkcus0ME8fNx5HRdKUzcPGlsSVAphJzut7W1I"
JSON_KEY = "credentials.json" 
st.set_page_config(page_title="庫存智能管家", layout="wide")
st.title("📦 庫存管理與智慧建議系統")

def upload_to_gsheets(file_path, sheet_name):
    """將 Excel 檔案內容上傳到特定的 Google Sheets 頁籤"""
    try:
        # 認證與連線
        scope = ["https://google.com", "https://googleapis.com"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEY, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).worksheet(sheet_name)

        # 讀取地端 Excel
        df = pd.read_excel(file_path)
        # 處理資料夾雜 NaN 的問題 (轉為空字串)
        df = df.fillna("")
        
        # 清空雲端原本的內容並寫入新內容
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist())
        
        print(f"✅ 成功將 {file_path} 上傳至雲端分頁：{sheet_name}")
    except Exception as e:
        print(f"❌ 上傳失敗: {e}")
# --- 執行上傳 ---
if __name__ == "__main__":
    # 上傳庫存表
    upload_to_gsheets("庫存表.xlsx", "庫存表")
    
    # 上傳營業紀錄
    upload_to_gsheets("營業紀錄.xlsx", "營業紀錄")
# --- 讀取資料函式 ---
def load_data_from_gs(sheet_name):
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
    # 嘗試讀取，若失敗則建立空表
    df_s = load_data_from_gs("作廢紀錄")
    st.session_state.df_scrap = df_s if not df_s.empty else pd.DataFrame(columns=['日期', '物品名稱', '數量', '原因'])

# --- 側邊欄：設定與上傳 ---
with st.sidebar:
    st.header("⚙️ 系統設定")
    line_token = st.text_input("LINE Notify Token", type="password")
    buffer_days = st.slider("建議補貨緩衝天數", 1, 30, 7)
    if st.button("重新讀取雲端資料"):
        st.session_state.clear()
        st.rerun()

# --- 主要頁面內容 ---
if st.session_state.df_inv is not None and not st.session_state.df_inv.empty:
    tab1, tab2, tab3 = st.tabs(["📊 庫存分析", "📉 執行作廢", "📜 作廢歷史紀錄"])

    with tab1:
        st.subheader("目前庫存狀態")
        df_display = st.session_state.df_inv.copy()
        df_display['有效期限'] = pd.to_datetime(df_display['有效期限'])
        st.dataframe(df_display, use_container_width=True)

        # 效期與建議邏輯 (同前，已優化顯示)
        today = datetime.now()
        expiry_info, suggestions = [], []
        last_year_range = [today - timedelta(days=380), today - timedelta(days=350)]

        for _, row in st.session_state.df_inv.iterrows():
            name, qty = row['物品名稱'], row['目前數量']
            days_left = (pd.to_datetime(row['有效期限']) - today).days
            if days_left < 0: expiry_info.append(f"❌ **{name}**: 已過期")
            elif days_left <= 7: expiry_info.append(f"⚠️ **{name}**: 快過期 ({max(0, days_left)}天)")
            
            # 叫貨建議 (簡單邏輯演示)
            if qty < 10: suggestions.append(f"📦 **{name}**: 庫存偏低，建議補貨")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🔔 效期預警")
            if expiry_info: 
                for m in expiry_info: st.warning(m)
            else: st.write("✅ 正常")
        with c2:
            st.markdown("#### 💡 叫貨建議")
            if suggestions:
                for s in suggestions: st.info(s)
            else: st.write("✅ 充足")

    with tab2:
        st.subheader("新增作廢紀錄")
        with st.form("scrap_form"):
            # 讓使用者從目前的庫存清單選擇
            item_list = st.session_state.df_inv['物品名稱'].tolist()
            selected_item = st.selectbox("選擇要作廢的物品", item_list)
            scrap_qty = st.number_input("作廢數量", min_value=1, step=1)
            scrap_reason = st.text_input("作廢原因 (如：破損、過期)")
            
            submit_btn = st.form_submit_button("確認提交作廢")

            if submit_btn:
                # 1. 更新庫存數據
                idx = st.session_state.df_inv[st.session_state.df_inv['物品名稱'] == selected_item].index
                current_stock = st.session_state.df_inv.at[idx[0], '目前數量']
                
                if current_stock >= scrap_qty:
                    st.session_state.df_inv.at[idx[0], '目前數量'] -= scrap_qty
                    
                    # 2. 增加作廢紀錄
                    new_log = pd.DataFrame([{
                        '日期': datetime.now().strftime('%Y-%m-%d %H:%M'),
                        '物品名稱': selected_item,
                        '數量': scrap_qty,
                        '原因': scrap_reason
                    }])
                    st.session_state.df_scrap = pd.concat([st.session_state.df_scrap, new_log], ignore_index=True)
                    
                    st.success(f"成功作廢 {selected_item} {scrap_qty} 件！請記得手動更新 Google Sheets 或 Excel 以永久存檔。")
                    st.balloons()
                else:
                    st.error("庫存數量不足，無法作廢！")

    with tab3:
        st.subheader("作廢歷史清單")
        if not st.session_state.df_scrap.empty:
            st.dataframe(st.session_state.df_scrap.sort_index(ascending=False), use_container_width=True)
        else:
            st.write("目前尚無作廢紀錄。")

else:
    st.info("💡 尚未讀取到庫存資料，請檢查 Google Sheets ID 或上傳檔案。")
