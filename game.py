import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- 遊戲介面設定 ---
st.set_page_config(page_title="可愛道具出租店", layout="wide")

# --- 1. 定義遊戲道具字典 (對應真實股票) ---
catalog = {
    "AAPL": {"name": "Canon 高階單眼相機", "emoji": "📷", "price": 170},
    "TSM": {"name": "AI 魔法晶片", "emoji": "💠", "price": 140},
    "NVDA": {"name": "傳說級運算核心", "emoji": "🔥", "price": 850},
    "GOOG": {"name": "全知水晶球", "emoji": "🔮", "price": 160},
    "MSFT": {"name": "Martin 頂級木吉他", "emoji": "🎸", "price": 400}
}

# --- 2. 模擬假資料 (未來這裡會接上 IBKR API) ---
# 閒置資金
cash_box = 15000.0  

# 庫存 (現股)
inventory = [
    {"symbol": "AAPL", "qty": 100},
    {"symbol": "MSFT", "qty": 200}
]

# 出租中 (賣出的 Call)
rented_out = [
    {"symbol": "TSM", "strike": 150, "dte": 12, "premium": 150.0},
    {"symbol": "NVDA", "strike": 900, "dte": 30, "premium": 850.0}
]

# --- 3. 繪製遊戲畫面 ---
st.title("🏪 收租小店長 - 營業儀表板")
st.markdown("歡迎光臨！這裡是我們的道具出租店，看看我們今天賺了多少金幣！")
st.divider()

# --- 頂部：金幣箱 ---
st.header("💰 老闆的金幣箱 (閒置資金)")
st.metric(label="可用金幣", value=f"${cash_box:,.2f} USD", delta="+ 本日收租入帳")
st.divider()

# --- 中間與底部：分為左右兩家店面 ---
col1, col2 = st.columns(2)

with col1:
    st.header("📦 倉庫架上 (等待出租)")
    st.info("這些是我們買進來的寶物，可以隨時租給客人喔！")
    
    if inventory:
        for item in inventory:
            sym = item['symbol']
            prop = catalog.get(sym, {"name": "神秘道具", "emoji": "❓"})
            
            # 使用 Streamlit 的卡片式排版
            st.success(f"{prop['emoji']} **{prop['name']}** ({sym})")
            st.write(f"▸ 庫存數量: {item['qty']} 個 (等於 {item['qty']/100:.0f} 組可出租)")
            st.button(f"出租 {sym}", key=f"rent_{sym}") # 假按鈕，按了還沒反應
            st.write("---")
    else:
        st.write("倉庫空空如也，老闆該進貨啦！")

with col2:
    st.header("⏳ 出租中 (收取租金中)")
    st.warning("客人已經付錢借走囉！等沙漏漏完，道具就會還給我們。")
    
    if rented_out:
        for item in rented_out:
            sym = item['symbol']
            prop = catalog.get(sym, {"name": "神秘道具", "emoji": "❓"})
            
            st.error(f"{prop['emoji']} **{prop['name']}** ({sym})")
            st.write(f"▸ 已經收到的租金: **${item['premium']} 金幣**")
            st.write(f"▸ 客人買斷價 (履約價): ${item['strike']}")
            st.write(f"▸ ⏳ 剩下 **{item['dte']} 天** 還回來")
            st.progress(max(0, 100 - item['dte']*2)) # 簡單的倒數進度條
            st.write("---")
    else:
        st.write("目前沒有道具出租中。")
