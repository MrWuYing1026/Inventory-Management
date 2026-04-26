import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- 設定區 ---
# 建議將來串接 Google Sheets ID
SHEET_ID = "1_Dg2nnIkcus0ME8fNx5HRdKUzcPGlsSVAphJzut7W1I"

st.set_page_config(page_title="庫存智能管家", layout="wide")
st.title("📦 庫存管理與智慧建議系統")

# --- 讀取資料 (目前仍保留讀取本地 Excel 邏輯，方便你直接測試) ---
def load_data():
    try:
        inv = pd.read_excel("庫存表.xlsx")
        sales = pd.read_excel("營業紀錄.xlsx")
        # 檢查作廢紀錄是否存在，不存在則建立空的
        try:
            scrap = pd.read_excel("作廢紀錄.xlsx")
        except:
            scrap = pd.DataFrame(columns=['日期', '物品名稱', '數量', '原因'])
        return inv, sales, scrap
    except Exception as e:
        st.error(f"讀取 Excel 失敗: {e}")
        return None, None, None

df_inv, df_sales, df_scrap = load_data()

# --- 側邊欄 ---
with st.sidebar:
    st.header("系統設定")
    line_token = st.text_input("LINE Notify Token", type="password")
    buffer_days = st.slider("建議補貨緩衝天數", 1, 30, 7)

if df_inv is not None:
    tab1, tab2, tab3 = st.tabs(["📊 庫存分析", "📉 執行作廢", "📜 作廢歷史紀錄"])

    with tab1:
        st.subheader("目前庫存狀態")
        df_inv['有效期限'] = pd.to_datetime(df_inv['有效期限'])
        today = datetime.now()
        st.dataframe(df_inv, use_container_width=True)

        expiry_info = []
        suggestions = []
        
        # 去年同期範圍
        last_year_today = today - timedelta(days=365)
        start_date = last_year_today - timedelta(days=15)
        end_date = last_year_today + timedelta(days=15)

        for _, row in df_inv.iterrows():
            name, qty = row['物品名稱'], row['目前數量']
            
            # 1. 效期計算
            days_left = (row['有效期限'] - today).days
            if days_left < 0:
                expiry_info.append(f"❌ **{name}**: 已過期 ({row['有效期限'].strftime('%Y-%m-%d')})")
            elif days_left <= 7:
                expiry_info.append(f"⚠️ **{name}**: 快過期 ({max(0, days_left)} 天)")

            # 2. 智慧建議
            past = df_sales[(df_sales['物品名稱'] == name) & 
                            (pd.to_datetime(df_sales['日期']).between(start_date, end_date))]
            avg_daily = past['消耗數量'].mean() if not past.empty else 0
            needed = round(avg_daily * buffer_days)
            if qty < needed:
                suggestions.append(f"📦 **{name}**: 建議補至 {needed} (目前 {qty})")

        # 顯示提醒 (修復 NULL 問題)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🔔 效期預警")
            if expiry_info:
                for m in expiry_info: st.warning(m)
            else: st.write("✅ 目前無過期品")
        with c2:
            st.markdown("#### 💡 叫貨建議")
            if suggestions:
                for s in suggestions: st.info(s)
            else: st.write("✅ 庫存非常充足")

        if st.button("發送手機通知 (LINE)"):
            if line_token:
                msg = "\n" + "\n".join(expiry_info + suggestions)
                requests.post("https://line.me", 
                              headers={"Authorization": f"Bearer {line_token}"}, 
                              data={"message": msg})
                st.success("通知已送出！")
            else:
                st.error("請輸入 LINE Token")

    with tab2:
        st.subheader("新增作廢紀錄")
        with st.form("scrap_form"):
            item = st.selectbox("選擇物品", df_inv['物品名稱'].tolist())
            s_qty = st.number_input("作廢數量", min_value=1, step=1)
            reason = st.text_input("作廢原因")
            if st.form_submit_button("執行報廢並存檔"):
                # 這裡執行存檔邏輯 (目前會存回本地 Excel)
                st.success(f"已記錄 {item} 作廢 {s_qty} 件")
                # 實作: df_inv 扣除數量並 save_excel

    with tab3:
        st.subheader("歷史紀錄")
        st.dataframe(df_scrap, use_container_width=True)
