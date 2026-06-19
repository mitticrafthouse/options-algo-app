import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Optional Dhan SDK if installed
try:
    from dhanhq import DhanHQ
except Exception:
    DhanHQ = None

IST = ZoneInfo("Asia/Kolkata")

st.set_page_config(page_title="Options Scalper", page_icon="📈", layout="wide")

# -----------------------------
# Secrets / config
# -----------------------------
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "")
DHAN_CLIENT_ID = st.secrets.get("DHAN_CLIENT_ID", "")
DHAN_ACCESS_TOKEN = st.secrets.get("DHAN_ACCESS_TOKEN", "")
DHAN_APP_ID = st.secrets.get("DHAN_APP_ID", "")
DHAN_APP_SECRET = st.secrets.get("DHAN_APP_SECRET", "")

# -----------------------------
# Authentication gate
# -----------------------------
def login_page():
    st.title("Login")
    st.caption("Secure access to the trading dashboard")
    with st.form("login_form"):
        user = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
    if submitted:
        if password == APP_PASSWORD:
            st.session_state["authenticated"] = True
            st.session_state["user"] = user or "trader"
            st.rerun()
        else:
            st.error("Invalid credentials")

if not st.session_state.get("authenticated", False):
    login_page()
    st.stop()

# -----------------------------
# Sidebar controls
# -----------------------------
st.sidebar.title("Trading Control")
mode = st.sidebar.radio("Mode", ["AUTO", "MANUAL", "BACKTEST"], horizontal=False)
index = st.sidebar.radio("Index", ["NIFTY", "SENSEX"], horizontal=True)
opt_type = st.sidebar.selectbox("Option Type", ["CE", "PE"])
signal_source = st.sidebar.radio("Data Source", ["LIVE", "HISTORICAL"], horizontal=True)
strike = st.sidebar.number_input("Strike", value=23500, step=50)
entry_premium = st.sidebar.number_input("Entry Premium", value=110.0, step=1.0)
target_pts = st.sidebar.number_input("Target Points", value=45.0, step=1.0)
sl_pts = st.sidebar.number_input("Stop Loss Points", value=12.0, step=1.0)
lots = st.sidebar.number_input("Lots", value=1, min_value=1, step=1)
lookback_days = st.sidebar.number_input("Backtest Days", value=20, min_value=5, max_value=365, step=1)

# -----------------------------
# Helpers
# -----------------------------
LOT_SIZES = {"NIFTY": 75, "SENSEX": 20}

def lot_size(symbol):
    return LOT_SIZES.get(symbol, 75)

def calc_trade(entry, target_pts, sl_pts, lots, symbol):
    qty = lot_size(symbol) * lots
    target = entry + target_pts
    sl = entry - sl_pts
    max_profit = qty * target_pts
    max_loss = qty * sl_pts
    rr = target_pts / sl_pts if sl_pts else 0
    return qty, target, sl, max_profit, max_loss, rr

def ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def vwap(df):
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    pv = tp * df["volume"]
    return pv.cumsum() / df["volume"].cumsum()

def generate_signal(df):
    if len(df) < 25:
        return {"signal": "WAIT", "reason": "Not enough candles"}
    x = df.copy()
    x["ema9"] = ema(x["close"], 9)
    x["ema21"] = ema(x["close"], 21)
    x["vwap"] = vwap(x)

    last = x.iloc[-1]
    prev = x.iloc[-2]

    bullish = prev["ema9"] <= prev["ema21"] and last["ema9"] > last["ema21"] and last["close"] > last["vwap"]
    bearish = prev["ema9"] >= prev["ema21"] and last["ema9"] < last["ema21"] and last["close"] < last["vwap"]

    if bullish:
        return {"signal": "BUY_CE", "reason": "EMA9 crossed above EMA21 and price above VWAP"}
    if bearish:
        return {"signal": "BUY_PE", "reason": "EMA9 crossed below EMA21 and price below VWAP"}
    return {"signal": "WAIT", "reason": "No valid crossover"}

def get_dhan_client():
    if DhanHQ is None:
        return None
    if DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN:
        return DhanHQ(client_id=DHAN_CLIENT_ID, access_token=DHAN_ACCESS_TOKEN)
    return None

# -----------------------------
# Dhan data fetchers
# -----------------------------
def fetch_historical_candles():
    # Replace with your actual Dhan historical endpoint / SDK call.
    # Use Dhan historical candles for backtest validation.
    end = datetime.now(IST)
    start = end - timedelta(days=int(lookback_days))

    rows = []
    price = 23500.0
    rng = np.random.default_rng(7)
    ts = pd.date_range(start=start, end=end, freq="5min", tz=IST)

    for t in ts:
        drift = rng.normal(0, 12)
        o = price
        c = max(1, o + drift)
        h = max(o, c) + abs(rng.normal(0, 4))
        l = min(o, c) - abs(rng.normal(0, 4))
        v = int(abs(rng.normal(100000, 20000)))
        rows.append([t, o, h, l, c, v])
        price = c

    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    return df

def fetch_live_candles_placeholder():
    # Hook this to Dhan live feed websocket aggregation.
    # Dhan live market feed is delivered over WebSocket.
    return fetch_historical_candles().tail(60)

def place_order_placeholder(side, symbol, strike, opt_type, qty, price=None):
    return {
        "status": "queued",
        "side": side,
        "symbol": symbol,
        "strike": strike,
        "type": opt_type,
        "qty": qty,
        "price": price,
        "message": "Replace with Dhan order placement API call"
    }

# -----------------------------
# Main layout
# -----------------------------
st.title("Options Scalper Dashboard")
st.caption("Live market signal engine with AUTO / MANUAL / BACKTEST support")

qty, target_px, sl_px, max_profit, max_loss, rr = calc_trade(
    entry_premium, target_pts, sl_pts, lots, index
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Quantity", f"{qty}")
c2.metric("Max Profit", f"₹{max_profit:,.0f}")
c3.metric("Max Loss", f"₹{max_loss:,.0f}")
c4.metric("Risk:Reward", f"1:{rr:.1f}")

left, right = st.columns([1.1, 0.9])

# Data selection
if mode == "BACKTEST" or signal_source == "HISTORICAL":
    candles = fetch_historical_candles()
else:
    candles = fetch_live_candles_placeholder()

signal = generate_signal(candles)
latest_close = float(candles.iloc[-1]["close"])
latest_vwap = float(vwap(candles).iloc[-1])
latest_ema9 = float(ema(candles["close"], 9).iloc[-1])
latest_ema21 = float(ema(candles["close"], 21).iloc[-1])

with left:
    st.subheader("Signal Panel")
    if signal["signal"] == "BUY_CE":
        st.success(f"BUY CE signal: {signal['reason']}")
        suggested_side = "BUY"
        suggested_type = "CE"
    elif signal["signal"] == "BUY_PE":
        st.error(f"BUY PE signal: {signal['reason']}")
        suggested_side = "BUY"
        suggested_type = "PE"
    else:
        st.info(signal["reason"])
        suggested_side = "WAIT"
        suggested_type = opt_type

    st.write(f"**Index:** {index}")
    st.write(f"**Strike:** {strike}")
    st.write(f"**Latest Close:** {latest_close:.2f}")
    st.write(f"**EMA 9:** {latest_ema9:.2f}")
    st.write(f"**EMA 21:** {latest_ema21:.2f}")
    st.write(f"**VWAP:** {latest_vwap:.2f}")
    st.write(f"**Entry:** ₹{entry_premium:.2f}")
    st.write(f"**Target:** ₹{target_px:.2f}")
    st.write(f"**Stop Loss:** ₹{sl_px:.2f}")

    if mode == "AUTO" and signal["signal"] in ["BUY_CE", "BUY_PE"]:
        order = place_order_placeholder(
            side="BUY",
            symbol=index,
            strike=int(strike),
            opt_type=suggested_type,
            qty=int(qty),
            price=None
        )
        st.warning(f"AUTO mode ready: {order['message']}")
    elif mode == "MANUAL" and signal["signal"] in ["BUY_CE", "BUY_PE"]:
        st.warning("MANUAL mode: show signal only, no order sent.")
    elif mode == "BACKTEST":
        st.info("BACKTEST mode: no live order will be sent.")

with right:
    st.subheader("Trade Settings")
    config_text = f"""APP_PASSWORD = "***"
DHAN_CLIENT_ID = "***"
DHAN_ACCESS_TOKEN = "***"
INDEX = "{index}"
MODE = "{mode}"
TARGET_POINTS = {target_pts}
SL_POINTS = {sl_pts}
LOTS = {lots}
LOT_SIZE = {lot_size(index)}
"""
    st.code(config_text, language="python")

st.divider()

tab1, tab2, tab3 = st.tabs(["Live / Backtest Data", "Trade Log", "Order Panel"])

with tab1:
    st.subheader("Candles")
    st.dataframe(candles.tail(50), use_container_width=True)

    st.subheader("Signal Validation")
    st.write({
        "signal": signal["signal"],
        "reason": signal["reason"],
        "latest_close": round(latest_close, 2),
        "ema9": round(latest_ema9, 2),
        "ema21": round(latest_ema21, 2),
        "vwap": round(latest_vwap, 2),
    })

with tab2:
    st.subheader("Sample Trade Log")
    trade_log = pd.DataFrame(
        [
            {"Time": "09:35", "Instrument": "NIFTY 23500 CE", "Entry": 118, "Exit": 163, "P&L": 3375, "Mode": "AUTO", "Result": "TARGET"},
            {"Time": "11:10", "Instrument": "NIFTY 23450 PE", "Entry": 95, "Exit": 83, "P&L": -900, "Mode": "MANUAL", "Result": "SL HIT"},
            {"Time": "13:45", "Instrument": "NIFTY 23500 CE", "Entry": 132, "Exit": 177, "P&L": 3375, "Mode": "AUTO", "Result": "TARGET"},
        ]
    )
    st.dataframe(trade_log, use_container_width=True, hide_index=True)
    st.write(f"Net P&L: ₹{trade_log['P&L'].sum():,.0f}")

with tab3:
    st.subheader("Place Order Preview")
    st.json(
        {
            "mode": mode,
            "suggested_signal": signal["signal"],
            "index": index,
            "strike": strike,
            "option_type": suggested_type,
            "qty": qty,
            "entry": entry_premium,
            "target": target_px,
            "stop_loss": sl_px,
        }
    )

    if st.button("Send Paper Order"):
        result = place_order_placeholder(
            side="BUY",
            symbol=index,
            strike=int(strike),
            opt_type=suggested_type,
            qty=int(qty),
            price=None,
        )
        st.success(result)
