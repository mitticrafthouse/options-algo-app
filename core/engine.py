import streamlit as st

def init_engine():
    if "trade" not in st.session_state:
        st.session_state.trade = None

    if "history" not in st.session_state:
        st.session_state.history = []


def create_trade(symbol, entry, qty):
    st.session_state.trade = {
        "symbol": symbol,
        "entry": entry,
        "qty": qty,
        "pnl": 0,
        "status": "OPEN",
        "sl": entry - 12,
        "target": entry + 45
    }


def update_trade(price):

    trade = st.session_state.trade
    if not trade:
        return

    pnl = (price - trade["entry"]) * trade["qty"]
    trade["pnl"] = pnl

    if price <= trade["sl"]:
        trade["status"] = "SL HIT"

    elif price >= trade["target"]:
        trade["status"] = "TARGET HIT"

    if trade["status"] != "OPEN":
        st.session_state.history.append(trade)
        st.session_state.trade = None
``