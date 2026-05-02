import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
from scipy.stats import norm
import matplotlib.pyplot as plt

# --- Black-Scholes 引擎 ---
def bs_delta(S, K, T, r, sigma, option_type):
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    return norm.cdf(d1) - 1.0 if option_type == 'put' else norm.cdf(d1)

def bs_price(S, K, T, r, sigma, option_type):
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if option_type == 'put':
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    else:
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)

def find_strike_by_delta(S, T, r, sigma, target_delta, option_type):
    best_K = S
    min_diff = 1.0
    search_range = np.linspace(S*0.3, S*1.2, 200) if option_type == 'put' else np.linspace(S*0.8, S*3.0, 200)
    for K in search_range:
        delta = bs_delta(S, K, T, r, sigma, option_type)
        if abs(delta - target_delta) < min_diff:
            min_diff = abs(delta - target_delta)
            best_K = K
    return round(best_K, 2)

# --- UI 介面設計 ---
st.set_page_config(page_title="滾輪法量化實驗室", layout="wide")
st.title("⚙️ 滾輪法 (The Wheel) 量化回測引擎")

col1, col2, col3 = st.columns(3)
with col1:
    ticker = st.text_input("輸入股票代號 (如 NVDA, TSLA)", value="NVDA")
    initial_capital = st.number_input("初始本金 (USD)", value=100000)
with col2:
    start_date = st.date_input("回測起始日", value=pd.to_datetime("2021-01-01"))
    end_date = st.date_input("回測結束日", value=pd.to_datetime("2026-01-01"))
with col3:
    target_delta = st.slider("目標 Delta 防線", min_value=0.05, max_value=0.50, value=0.30, step=0.05)
    slippage = st.slider("滑價與手續費保留比例 (0.9 = 扣除10%)", min_value=0.80, max_value=1.00, value=0.90, step=0.01)

if st.button("🚀 啟動回測", type="primary"):
    with st.spinner(f"正在從 Yahoo Finance 下載 {ticker} 歷史資料並進行運算..."):
        # --- 抓取資料 ---
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if df.empty:
            st.error("找不到資料，請確認股票代號或日期！")
            st.stop()
            
        close_prices = df['Close'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Close']
        df_sim = pd.DataFrame({'Close': close_prices})
        df_sim['Return'] = df_sim['Close'].pct_change()
        df_sim['HV'] = df_sim['Return'].rolling(window=21).std() * np.sqrt(252)
        df_sim = df_sim.dropna()

        dates = df_sim.index
        prices = df_sim['Close'].values
        hvs = df_sim['HV'].values

        # --- 回測狀態機 ---
        state = "CASH"
        cash = initial_capital
        shares = 0
        bh_shares = initial_capital / prices[0]
        r = 0.04
        DTE = 21
        
        trade_log = []
        nav_history = []
        total_premium = 0

        for i in range(0, len(prices) - DTE, DTE):
            today = dates[i]
            exp_date = dates[i + DTE]
            current_price = prices[i]
            exp_price = prices[i + DTE]
            current_iv = max(hvs[i], 0.25)
            T = DTE / 252.0
            
            if state == "CASH":
                K = find_strike_by_delta(current_price, T, r, current_iv, -target_delta, 'put')
                premium = bs_price(current_price, K, T, r, current_iv, 'put') * slippage
                num_options = cash / K
                cash += premium * num_options
                total_premium += premium * num_options
                
                trade_log.append({"日期": today.strftime('%Y-%m-%d'), "動作": "Sell Put", "現價": round(current_price, 2), "履約價": K, "收租 ($)": round(premium * num_options, 0), "狀態": "滿手現金"})
                
                if exp_price <= K:
                    shares = cash / K
                    cash = 0
                    state = "STOCK"
                    
            elif state == "STOCK":
                K = find_strike_by_delta(current_price, T, r, current_iv, target_delta, 'call')
                premium = bs_price(current_price, K, T, r, current_iv, 'call') * slippage
                cash += premium * shares
                total_premium += premium * shares
                
                trade_log.append({"日期": today.strftime('%Y-%m-%d'), "動作": "Sell Call", "現價": round(current_price, 2), "履約價": K, "收租 ($)": round(premium * shares, 0), "狀態": "滿手股票"})
                
                if exp_price >= K:
                    cash += shares * K
                    shares = 0
                    state = "CASH"

            nav_history.append({"Date": exp_date, "Wheel_NAV": cash + (shares * exp_price), "BH_NAV": bh_shares * exp_price})

        # --- 結算與圖表 ---
        df_nav = pd.DataFrame(nav_history)
        df_log = pd.DataFrame(trade_log)
        final_wheel = df_nav['Wheel_NAV'].iloc[-1]
        final_bh = df_nav['BH_NAV'].iloc[-1]
        
        st.success("回測完成！")
        
        # 顯示 KPI 卡片
        m1, m2, m3 = st.columns(3)
        m1.metric("Buy & Hold 終局資產", f"${final_bh:,.0f}")
        m2.metric("滾輪法 終局資產", f"${final_wheel:,.0f}")
        m3.metric("滾輪法 總收租金 (純現金流)", f"${total_premium:,.0f}")

        # 繪製走勢圖
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(df_nav['Date'], df_nav['BH_NAV'], label='Buy & Hold', color='#2ca02c')
        ax.plot(df_nav['Date'], df_nav['Wheel_NAV'], label=f'The Wheel (\u0394 {target_delta})', color='#1f77b4', linewidth=2)
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.5)
        st.pyplot(fig)

        # 提供 CSV 下載與明細預覽
        st.subheader("📝 交易明細日誌")
        csv = df_log.to_csv(index=False).encode('utf-8-sig')
        st.download_button(label="📥 下載完整交易明細 (CSV)", data=csv, file_name=f"{ticker}_wheel_log.csv", mime='text/csv')
        st.dataframe(df_log)
