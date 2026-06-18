import sys
import os


# ✅ FIX: Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import streamlit as st
import time
from core.engine import init_engine, create_trade, update_trade
from core.websocket import get_live_price
from services.dhan import place_order
from utils.ui import pnl_bar



init_engine()

st.title("⚡ Trading Dashboard")

# SAMPLE SIGNAL (replace with real)
symbol = "NIFTY23500CE"
entry = 110
qty = 65

if st.button("🚀 Start Trade"):
    create_trade(symbol, entry, qty)
    res = place_order(symbol, qty)
    st.success(res)

# ACTIVE TRADE
if st.session_state.trade:

    trade = st.session_state.trade

    price = get_live_price(trade["entry"])

    update_trade(price)

    st.subheader("📊 Live Trade")

    st.write(f"Symbol: {trade['symbol']}")
    st.write(f"Entry: ₹{trade['entry']}")
    st.write(f"Live: ₹{price}")

    pnl_bar(trade["pnl"])

    st.write(f"SL: {trade['sl']} | Target: {trade['target']}")
    st.write(f"Status: {trade['status']}")

    time.sleep(1)
    st.rerun()
