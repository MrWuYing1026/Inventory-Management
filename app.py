import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- 網頁配置 ---
st.set_page_config(page_title="庫存智能管家", layout="wide")
st.title("📦 庫存管理與智慧建議系統")

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("設定")
    line_token = st.text_input("LINE Notify Token", type="password")
    buffer_days = st.slider("建議補貨緩衝天數", 1, 30, 10)
    st.info("💡 提示：Token 可至 LINE Notify 官網申請")

# --- 讀取檔案邏輯 ---
def load_data():
    try:
        inv = pd.read_excel("庫存表.xlsx")
        sales = pd.read_excel("營業紀錄.xlsx")
        return inv, sales
    except:
        return None, None

df_inv, df_sales = load_data()

if df_inv is not None:
    # --- 頁面標籤 ---
    tab1, tab2, tab3 = st.tabs(["📊 當前庫存與分析", "📜 作廢紀錄", "⚙️ 資料維護"])

    with tab1:
        st.subheader("庫存狀態")
        
        # 數據預處理
        df_inv['有效期限'] = pd.to_datetime(df_inv['有效期限'])
        df_sales['日期'] = pd.to_datetime(df_sales['日期'])
        today = datetime.now()
        
        # 計算智能建議
        suggestions = []
        expiry_info = []
        
        last_year_today = today - timedelta(days=365)
        start_date = last_year_today - timedelta(days=15)
        end_date = last_year_today + timedelta(days=15)

        # 顯示表格並標色
        def highlight_status(row):
            # 效期檢查
            days_left = (row['有效期限'] - today).days
            if days_left < 0: return ['background-color: #ffcccc'] * len(row) # 已過期
            if days_left <= 7: return ['background-color: #fff3cd'] * len(row) # 快過期
            return [''] * len(row)

        st.dataframe(df_inv.style.apply(highlight_status, axis=1), use_container_width=True)

        # --- 核心邏輯計算 ---
        for _, row in df_inv.iterrows():
            name = row['物品名稱']
            qty = row['目前數量']
            
            # 智慧建議
            past = df_sales[(df_sales['物品名稱'] == name) & (df_sales['日期'].between(start_date, end_date))]
            avg_sales = past['消耗數量'].mean() if not past.empty else 0
            needed = round(avg_sales * buffer_days)
            
            if qty < needed:
                suggestions.append(f"📦 **{name}**: 建議補至 {needed} (目前 {qty})")
            
            days_left = (row['有效期限'] - today).days
            if days_left < 0:
                expiry_info.append(f"❌ **{name}**: 已過期！")
            elif days_left <= 7:
                expiry_info.append(f"⚠️ **{name}**: 將於 {days_left} 天內過期")

        # --- 側邊顯示結果 ---
        col1, col2 = st.columns(2)
        with col1:
            st.warning("🔔 效期預警")
            for msg in expiry_info: st.write(msg)
        with col2:
            st.success("💡 叫貨建議")
            for msg in suggestions: st.write(msg)

        # --- 發送通知按鈕 ---
        if st.button("發送手機通知 (LINE)"):
            if not line_token:
                st.error("請先在左側輸入 LINE Token")
            else:
                report = "【庫存報告】\n" + "\n".join(expiry_info + suggestions)
                headers = {"Authorization": f"Bearer {line_token}"}
                requests.post("https://line.me", headers=headers, data={"message": report})
                st.balloons()
                st.success("通知已送出！")

    with tab2:
        st.write("此處可串接作廢紀錄功能...")
        # 可在此加入 st.data_editor 讓使用者直接在網頁輸入作廢資訊

    with tab3:
        st.write("您可以直接在 Excel 修改資料後重新整理網頁。")
        if st.button("重新讀取 Excel"):
            st.rerun()

else:
    st.error("找不到 Excel 檔案！請確保 '庫存表.xlsx' 與 '營業紀錄.xlsx' 放在程式資料夾中。")
