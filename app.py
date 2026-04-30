import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.stats import norm
from datetime import datetime

# --- 核心運算邏輯 (Black-Scholes Delta) ---
def calculate_call_delta(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0: return 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    return norm.cdf(d1)

# --- App 介面設定 ---
st.set_page_config(page_title="美股收租即時儀表板", layout="wide")
st.title("📊 美股收租即時掃描器 (下單增強版)")
st.write(f"目前時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 側邊欄參數 (方便調整)
with st.sidebar:
    st.header("⚙️ 參數設定")
    tickers_input = st.text_input("股票池 (逗號分隔)", "TSM,GOOG,AAPL,NVDA,MSFT,AMZN")
    target_delta = st.slider("目標 Delta", 0.01, 0.20, 0.08)
    min_roi = st.number_input("最低年化報酬率門檻 (%)", value=4.5)
    dte_range = st.slider("到期天數範圍 (DTE)", 10, 60, (30, 45))

# 主按鈕
if st.button('🚀 立即更新即時數據'):
    tickers = [t.strip() for t in tickers_input.split(',')]
    results = []
    best_option = None
    best_score = 999
    
    with st.spinner('正在連線華爾街抓取即時報價...'):
        for symbol in tickers:
            try:
                stock = yf.Ticker(symbol)
                hist = stock.history(period="1d")
                if hist.empty: continue
                current_price = hist['Close'].iloc[-1]
                
                for date_str in stock.options:
                    exp_date = datetime.strptime(date_str, '%Y-%m-%d')
                    dte = (exp_date - datetime.now()).days
                    if dte_range[0] <= dte <= dte_range[1]:
                        opt_chain = stock.option_chain(date_str)
                        calls = opt_chain.calls
                        T_years = dte / 365.0
                        
                        # 計算 Delta
                        calls['Delta'] = calls.apply(lambda r: calculate_call_delta(current_price, r['strike'], T_years, 0.045, r['impliedVolatility']), axis=1)
                        safe_calls = calls[calls['strike'] > current_price].copy().sort_values('strike').reset_index(drop=True)
                        
                        if not safe_calls.empty:
                            best_idx = abs(safe_calls['Delta'] - target_delta).idxmin()
                            
                            def get_data(idx):
                                if idx < 0 or idx >= len(safe_calls): return None
                                c = safe_calls.iloc[idx]
                                mid = round((c['bid'] + c['ask']) / 2, 2)
                                roi = (mid / current_price) * (365 / max(1, dte)) * 100
                                return {"strike": c['strike'], "mid": mid, "delta": c['Delta'], "roi": roi, "dte": dte, "exp": date_str}

                            # 按照你的需求排序：一般 -> 保守 -> 積極
                            ops = {
                                "一般型": get_data(best_idx),
                                "保守型": get_data(best_idx + 1),
                                "積極型": get_data(best_idx - 1)
                            }
                            
                            row = {"代號": symbol, "現價": round(current_price, 2), "到期日": f"{date_str}({dte}d)"}
                            for k, v in ops.items():
                                if v:
                                    txt = f"${v['strike']}(${v['mid']}) - Δ{v['delta']:.4f}({v['roi']:.1f}%)"
                                    row[k] = txt
                                    # 篩選最佳推薦標的
                                    if v['roi'] >= min_roi:
                                        score = abs(v['delta'] - 0.1)
                                        if score < best_score:
                                            best_score = score
                                            best_option = {
                                                "stock": symbol, 
                                                "text": txt, 
                                                "strike": v['strike'], 
                                                "mid": v['mid'], 
                                                "exp": v['exp'],
                                                "type": k
                                            }
                            results.append(row)
                        break
            except Exception as e:
                st.error(f"無法抓取 {symbol}: {e}")

    # 顯示主報表
    if results:
        if best_option:
            st.success(f"🏆 本日最推薦：{best_option['stock']} -> {best_option['text']}")
        
        df_display = pd.DataFrame(results)
        cols = ["代號", "現價", "到期日", "一般型", "保守型", "積極型"]
        st.dataframe(df_display[cols], use_container_width=True)
        
        # --- 🚀 下單傳送門區域 ---
        if best_option:
            st.markdown("---")
            st.subheader(f"⚡ 快速下單傳送門 ({best_option['stock']})")
            
            c1, c2 = st.columns([1, 2])
            with c1:
                # 生成 Firstrade 手機版網頁的深層連結
                ft_url = f"https://invest.firstrade.com/cgi-bin/main#/trade/option/{best_option['stock']}"
                st.link_button(f"🔗 開啟 Firstrade 交易 {best_option['stock']}", ft_url)
                st.info("💡 點擊上方按鈕可直接跳轉至該股票期權頁面")
            
            with c2:
                # 建立方便複製的指令字串
                cmd = f"{best_option['stock']} | Sell Open | {best_option['exp']} | Strike: ${best_option['strike']} | Limit: ${best_option['mid']}"
                st.write("📋 下單指令 (點擊右上角按鈕複製):")
                st.code(cmd, language='text')
                
        st.balloons()
    else:
        st.warning("目前沒有符合條件的標的。")
