import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

# =========================
# CONFIG
# =========================
MIN_BALANCE = 500

INDICES = {
    "NIFTY": {"lot": 65, "step": 50},
    "BANKNIFTY": {"lot": 30, "step": 100},
    "FINNIFTY": {"lot": 60, "step": 50},
    "SENSEX": {"lot": 20, "step": 100}
}

CLIENT_ID = st.secrets.get("CLIENT_ID", "")
ACCESS_TOKEN = st.secrets.get("ACCESS_TOKEN", "")

# =========================
# LOGIN
# =========================
USERS = {"admin": "admin123"}

def login():
    st.sidebar.title("🔐 Login")
    u = st.sidebar.text_input("User")
    p = st.sidebar.text_input("Pass", type="password")

    if st.sidebar.button("Login"):
        if USERS.get(u) == p:
            st.session_state["logged"] = True

    return st.session_state.get("logged", False)

# =========================
# WALLET
# =========================
def get_wallet_balance():
    try:
        from dhanhq import dhanhq
        client = dhanhq(CLIENT_ID, ACCESS_TOKEN)
        data = client.get_fund_limits()
        return data["data"].get("availabelBalance", 0)
    except:
        return 0

def init_system():
    if "balance" not in st.session_state:
        st.session_state["balance"] = get_wallet_balance()

    st.session_state["auto"] = st.session_state["balance"] >= MIN_BALANCE

    if "active_trade" not in st.session_state:
        st.session_state["active_trade"] = None

    if "trade_log" not in st.session_state:
        st.session_state["trade_log"] = []

    if "last_trade_time" not in st.session_state:
        st.session_state["last_trade_time"] = None

# =========================
# NSE FETCH
# =========================
@st.cache_data(ttl=10)
def get_option_chain(symbol):
    try:
        session = requests.Session()
        headers = {"User-Agent": "Mozilla/5.0"}

        session.get("https://www.nseindia.com", headers=headers)
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"

        res = session.get(url, headers=headers)

        return res.json()
    except:
        return None

# =========================
# BUILD MARKET STRUCTURE
# =========================
def build_market_structure(data):
    prices = []

    for row in data["records"]["data"][:40]:
        if "CE" in row:
            prices.append(row["CE"]["lastPrice"])

    df = pd.DataFrame({"close": prices})

    df["ema9"] = df["close"].ewm(span=9).mean()
    df["ema21"] = df["close"].ewm(span=21).mean()
    df["vwap"] = df["close"].expanding().mean()

    return df

# =========================
# AI FILTER
# =========================
def ai_filter(row):
    score = 0

    if row["ema9"] > row["ema21"]:
        score += 0.4

    if row["close"] > row["vwap"]:
        score += 0.4

    if row["close"] > row["ema9"]:
        score += 0.2

    return score > 0.6

# =========================
# SIGNAL
# =========================
def generate_signal(df):

    latest = df.iloc[-1]

    if latest["ema9"] > latest["ema21"] and ai_filter(latest):
        return "BUY CE"

    if latest["ema9"] < latest["ema21"] and ai_filter(latest):
        return "BUY PE"

    return None

# =========================
# ATM OPTION
# =========================
def get_atm_option(data, signal):

    spot = data["records"]["underlyingValue"]

    closest = min(
        data["records"]["data"],
        key=lambda x: abs(x["strikePrice"] - spot)
    )

    if "CE" in signal:
        opt = closest.get("CE", {})
    else:
        opt = closest.get("PE", {})

    return opt, closest["strikePrice"], spot

# =========================
# SYMBOL
# =========================
def get_expiry():
    today = datetime.now()
    th = today + timedelta((3 - today.weekday()) % 7)
    return th.strftime("%d%b%y").upper()

def build_symbol(index, strike, opt):
    return f"{index}{get_expiry()}{int(strike)}{opt}"

# =========================
# POSITION SIZE
# =========================
def position_size(index):
    capital = st.session_state["balance"]

    if capital <= 0:
        return INDICES[index]["lot"]

    risk = capital * 0.01
    lot = INDICES[index]["lot"]

    qty = int(risk / 12)

    return max(lot, (qty // lot) * lot)

# =========================
# TRADE ENGINE
# =========================
def can_trade():
    if st.session_state["last_trade_time"] is None:
        return True

    diff = (datetime.now() - st.session_state["last_trade_time"]).seconds
    return diff > 300  # 5 min cooldown


def enter_trade(symbol, entry, qty):

    st.session_state["active_trade"] = {
        "symbol": symbol,
        "entry": entry,
        "qty": qty,
        "sl": entry - 12,
        "target": entry + 45,
        "status": "OPEN"
    }

    st.session_state["last_trade_time"] = datetime.now()


def manage_trade(current_price):

    trade = st.session_state["active_trade"]

    if not trade:
        return

    entry = trade["entry"]

    profit = current_price - entry

    if profit > 15:
        trade["sl"] = entry
    if profit > 25:
        trade["sl"] = entry + 10
    if profit > 35:
        trade["sl"] = entry + 20

    if current_price <= trade["sl"]:
        trade["status"] = "SL HIT"

    elif current_price >= trade["target"]:
        trade["status"] = "TARGET HIT"

    if trade["status"] != "OPEN":
        st.session_state["trade_log"].append(trade)
        st.session_state["active_trade"] = None

# =========================
# ORDER
# =========================
def place_order(symbol, qty):

    if not st.session_state["auto"]:
        return "❌ LOW BALANCE - BLOCKED"

    try:
        from dhanhq import dhanhq
        client = dhanhq(CLIENT_ID, ACCESS_TOKEN)

        client.place_order(
            trading_symbol=symbol,
            exchange_segment="NSE_FNO",
            transaction_type="BUY",
            quantity=qty,
            order_type="MARKET",
            product_type="INTRADAY"
        )

        return "✅ ORDER EXECUTED"

    except Exception as e:
        return f"❌ {e}"

# =========================
# UI START
# =========================
st.set_page_config(layout="wide")

if not login():
    st.stop()

init_system()

page = st.sidebar.radio("Page", ["Trading", "Profile"])

# =========================
# PROFILE
# =========================
if page == "Profile":

    st.title("👤 Portfolio Dashboard")

    bal = st.session_state["balance"]

    st.metric("Wallet Balance", f"₹{bal}")

    if bal < MIN_BALANCE:
        st.error("Low Balance")
    else:
        st.success("Ready")

    st.subheader("Trade History")
    st.dataframe(st.session_state["trade_log"])

    st.stop()

# =========================
# TRADING UI
# =========================
st.title("🚀 Real Algo Trading Engine")

bal = st.session_state["balance"]

if bal < MIN_BALANCE:
    st.error("Low balance → AUTO OFF")
else:
    st.success("System Ready")

mode = st.sidebar.radio("Mode", ["AUTO", "MANUAL"])

if bal < MIN_BALANCE:
    mode = "MANUAL"

index = st.selectbox("Index", list(INDICES.keys()))

data = get_option_chain(index)

if not data:
    st.error("NSE fetch failed")
    st.stop()

df = build_market_structure(data)

signal = generate_signal(df)

st.line_chart(df[["close", "ema9", "ema21"]])

# =========================
# SIGNAL EXECUTION
# =========================
if signal and can_trade() and st.session_state["active_trade"] is None:

    opt, strike, spot = get_atm_option(data, signal)

    opt_type = "CE" if "CE" in signal else "PE"
    symbol = build_symbol(index, strike, opt_type)

    price = opt.get("lastPrice", 0)
    qty = position_size(index)

    st.success(f"{signal} → {symbol} @ ₹{price}")

    if mode == "AUTO":
        res = place_order(symbol, qty)
        st.info(res)

        if "✅" in res:
            enter_trade(symbol, price, qty)

else:
    st.warning("No Trade / Cooldown / Active Trade Running")

# =========================
# ACTIVE TRADE MONITOR
# =========================
if st.session_state["active_trade"]:

    trade = st.session_state["active_trade"]

    current = trade["entry"] + np.random.randint(-10, 50)

    manage_trade(current)

    st.subheader("📊 Active Trade")

    st.write(f"""
    Symbol: {trade['symbol']}  
    Entry: ₹{trade['entry']}  
    Current: ₹{current}  
    SL: ₹{trade['sl']}  
    Target: ₹{trade['target']}  
    Status: {trade['status']}
    """)
``
