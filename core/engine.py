import streamlit as st

# =========================
# INIT ENGINE
# =========================
def init_engine():

    if "trade" not in st.session_state:
        st.session_state.trade = None

    if "history" not in st.session_state:
        st.session_state.history = []


# =========================
# CREATE TRADE
# =========================
def create_trade(symbol, entry, qty):

    st.session_state.trade = {
        "symbol": symbol,
        "entry": entry,
        "qty": qty,
        "pnl": 0,
        "sl": entry - 12,
        "target": entry + 45,
        "status": "OPEN"
    }


# =========================
# UPDATE TRADE
# =========================
def update_trade(price):

    trade = st.session_state.trade

    if not trade:
        return

    entry = trade["entry"]
    qty = trade["qty"]

    pnl = (price - entry) * qty
    trade["pnl"] = pnl

    if price <= trade["sl"]:
        trade["status"] = "SL HIT"

    elif price >= trade["target"]:
        trade["status"] = "TARGET HIT"

    if trade["status"] != "OPEN":
        st.session_state.history.append(trade)
        st.session_state.trade = None
