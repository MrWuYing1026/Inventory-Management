import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import os

# --- 設定區 ---
INVENTORY_FILE = "庫存表.xlsx"
SALES_FILE = "營業紀錄.xlsx"
SCRAP_FILE = "作廢紀錄.xlsx"

st.set_page_config(page_title="庫存智能管家", layout="wide")
st.title("📦 庫存管理與智慧建議系統")

# --- 讀取/儲存函式 ---
def load_data():
    inv = pd.read_excel(INVENTORY_FILE) if os.path.exists(INVENTORY_FILE) else pd.DataFrame(columns=['物品名稱', '目前數量', '有效期限'])
    sales = pd.read_excel(SALES_FILE) if os.path.exists(SALES_FILE) else pd.DataFrame(columns=['日期', '物品名稱', '消耗數量'])
    scrap = pd.read_excel(SCRAP_FILE) if os.path.exists(SCRAP_FILE) else pd.DataFrame(columns=['日期', '物品名稱', '數量', '原因'])
    return inv, sales, scrap

def save_data(df, filename):
    df.to_excel(filename, index=False)

# 載入資料
df_inv, df_sales, df_scrap = load_data()

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("系統設定")
    line_token = st.text_input("LINE Notify Token", type="password")
    buffer_days = st.slider("建議補貨緩衝天數", 1, 30, 7)

if not df_inv.empty:
    tab1, tab2, tab3 = st.tabs(["📊 庫存分析", "📉 執行作廢", "📜 作廢歷史紀錄"])

    with tab1:
        st.subheader("目前庫存狀態")
        df_inv['有效期限'] = pd.to_datetime(df_inv['有效期限'])
        today = datetime.now()
        
        # 顯示表格 (含效期標色)
        st.dataframe(df_inv, use_container_width=True)

        # 智慧建議與效期計算
        suggestions = []
        expiry_info = []
        last_year_range = [today - timedelta(days=380), today - timedelta(days=350)]

        for _, row in df_inv.iterrows():
            name, qty = row['物品名稱'], row['目前數量']
            # 效期檢查
            days_left = (row['有效期限'] - today).days
            if days_left < 0: expiry_info.append(f"❌ **{name}**: 已過期！")
            elif days_left <= 7: expiry_info.append(f"⚠️ **{name}**: 快過期 ({days_left}天)")

            # 叫貨建議
            past = df_sales[(df_sales['物品名稱'] == name) & (pd.to_datetime(df_sales['日期']).between(last_year_range[0], last_year_range[1]))]
            needed = round(past['消耗數量'].mean() * buffer_days) if not past.empty else 0
            if qty < needed: suggestions.append(f"📦 **{name}**: 建議補至 {needed} (現有{qty})")

        c1, c2 = st.columns(2)
        with c1: st.warning("🔔 效期預警"); [st.write(m) for m in expiry_info]
        with c2: st.success("💡 叫貨建議"); [st.write(m) for m in suggestions]

    with tab2:
        st.subheader("新增作廢紀錄")
        with st.form("scrap_form"):
            item_to_scrap = st.selectbox("選擇物品", df_inv['物品名稱'].tolist())
            qty_to_scrap = st.number_input("作廢數量", min_value=1, step=1)
            reason = st.text_input("作廢原因", placeholder="例如：過期、損壞")
            submitted = st.form_submit_button("確認作廢")

            if submitted:
                # 1. 更新庫存
                idx = df_inv[df_inv['物品名稱'] == item_to_scrap].index[0]
                if df_inv.at[idx, '目前數量'] >= qty_to_scrap:
                    df_inv.at[idx, '目前數量'] -= qty_to_scrap
                    save_data(df_inv, INVENTORY_FILE)
                    
                    # 2. 寫入作廢紀錄
                    new_log = pd.DataFrame([{
                        '日期': today.strftime('%Y-%m-%d %H:%M'),
                        '物品名稱': item_to_scrap,
                        '數量': qty_to_scrap,
                        '原因': reason
                    }])
                    df_scrap = pd.concat([df_scrap, new_log], ignore_index=True)
                    save_data(df_scrap, SCRAP_FILE)
                    
                    st.success(f"成功作廢 {item_to_scrap} {qty_to_scrap} 件！庫存已更新。")
                    st.rerun()
                else:
                    st.error("錯誤：作廢數量大於現有庫存！")

    with tab3:
        st.subheader("歷史作廢清單")
        st.dataframe(df_scrap.sort_values(by='日期', ascending=False), use_container_width=True)

else:
    st.error("尚未讀取到庫存資料，請確認 Excel 檔案。")
