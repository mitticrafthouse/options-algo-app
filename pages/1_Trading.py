import streamlit as st
import sys
import os
import time

# ✅ FORCE PROJECT ROOT RESOLUTION
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# ✅ SAFE IMPORT (TRY + FALLBACK)
try:
    from core.engine import init_engine, create_trade, update_trade
    from core.websocket import get_live_price
    from services.dhan import place_order, get_balance
    from utils.ui import pnl_bar
except Exception as e:
    st.error(f"Import Error: {e}")
    st.stop()

# =========================
# INIT ENGINE
# =========================
init_engine()

st.set_page_config(layout="wide")
st.title("⚡ Trading Dashboard")

# =========================
# GET BALANCE
# =========================
balance = get_balance()
st.sidebar.metric("💰 Wallet", f"₹{balance}")

# =========================
# SAMPLE DATA (replace later)
# =========================
symbol = "NIFTY23500CE"
entry_price = 110
qty = 65

st.markdown("---")

# =========================
# SIGNAL UI
# =========================
st.subheader("📡 Live Signal")

c1, c2, c3 = st.columns(3)
c1.metric("Symbol", symbol)
c2.metric("Entry", f"₹{entry_price}")
c3.metric("Qty", qty)

# =========================
# EXECUTE
# =========================
if st.button("🚀 Execute Trade"):

    if balance < 500:
        st.error("❌ Low Balance")
    else:
        result = place_order(symbol, qty)
        st.success(result)

        if "✅" in result:
            create_trade(symbol, entry_price, qty)

# =========================
# ACTIVE TRADE MONITOR
# =========================
if "trade" in st.session_state and st.session_state.trade:

    trade = st.session_state.trade

    live_price = get_live_price(trade["entry"])
    update_trade(live_price)

    st.markdown("---")
    st.subheader("📊 Active Trade")

    c1, c2, c3 = st.columns(3)

    c1.metric("Entry", f"₹{trade['entry']}")
    c2.metric("Live", f"₹{live_price}")
    c3.metric("Qty", trade["qty"])

    pnl_bar(trade["pnl"])

    st.write(f"🎯 Target: ₹{trade['target']}")
    st.write(f"🛑 SL: ₹{trade['sl']}")
    st.write(f"📌 Status: {trade['status']}")

    time.sleep(1)
    st.rerun()

else:
    st.info("No active trade")

# =========================
# TRADE HISTORY
# =========================
st.markdown("---")
st.subheader("📘 Trade History")

if "history" in st.session_state and st.session_state.history:
    st.dataframe(st.session_state.history)
else:
    st.write("No trades yet")
