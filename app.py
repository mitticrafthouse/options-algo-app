import streamlit as st
import numpy as np
import requests
from datetime import datetime, timedelta

# =========================
# CONFIG ✅ CORRECT LOT SIZE
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
    st.sidebar.title("Login")
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

def check_auto():
    bal = get_wallet_balance()
    return bal >= MIN_BALANCE, bal

# =========================
# NSE OPTION CHAIN (LIVE)
# =========================
def get_option_chain(symbol):
    try:
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US"
        }

        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers)
        data = session.get(url, headers=headers).json()

        return data
    except:
        return None

# =========================
# SPOT PRICE FROM CHAIN
# =========================
def get_spot_from_chain(data):
    return data["records"]["underlyingValue"]

# =========================
# FIND ATM STRIKE
# =========================
def get_atm_option(data, signal):
    spot = get_spot_from_chain(data)

    closest = None
    min_diff = float("inf")

    for row in data["records"]["data"]:
        strike = row["strikePrice"]
        diff = abs(strike - spot)

        if diff < min_diff:
            min_diff = diff
            closest = row

    if "CE" in signal:
        opt = closest.get("CE", {})
    else:
        opt = closest.get("PE", {})

    return opt, closest["strikePrice"], spot

# =========================
# EXPIRY (NEXT THURSDAY)
# =========================
def get_expiry():
    today = datetime.now()
    next_thursday = today + timedelta((3 - today.weekday()) % 7)
    return next_thursday.strftime("%d%b%y").upper()

# =========================
# BUILD TRADING SYMBOL ✅ NO CSV
# =========================
def build_symbol(index, strike, opt_type):
    expiry = get_expiry()

    # Example: NIFTY 27JUN24 23500 CE
    return f"{index}{expiry}{int(strike)}{opt_type}"

# =========================
# SIGNAL (TEMP - replace later)
# =========================
def generate_signal():
    return np.random.choice(["BUY CE", "BUY PE", None], p=[0.4,0.4,0.2])

# =========================
# POSITION SIZE
# =========================
def position_size(index, sl=12):
    capital = get_wallet_balance()

    if capital <= 0:
        return INDICES[index]["lot"]

    risk = capital * 0.01
    lot = INDICES[index]["lot"]

    qty = int(risk / sl)
    lots = max(1, qty // lot)

    return lots * lot

# =========================
# ORDER (SYMBOL BASED)
# =========================
def place_order(symbol, qty):
    try:
        from dhanhq import dhanhq
        client = dhanhq(CLIENT_ID, ACCESS_TOKEN)

        client.place_order(
            trading_symbol=symbol,  # ✅ symbol instead of security_id
            exchange_segment="NSE_FNO",
            transaction_type="BUY",
            quantity=qty,
            order_type="MARKET",
            product_type="INTRADAY"
        )

        return f"✅ Order {symbol}"

    except Exception as e:
        return f"❌ {e}"

# =========================
# UI
# =========================
st.set_page_config(layout="wide")

if not login():
    st.stop()

st.title("🚀 LIVE NSE OPTIONS (NO CSV)")

auto_ok, bal = check_auto()

mode = st.sidebar.radio("Mode", ["AUTO", "MANUAL"])
st.sidebar.write(f"Balance: ₹{bal}")

if not auto_ok:
    st.error("Low Balance → AUTO OFF")
    mode = "MANUAL"

index = st.selectbox("Index", list(INDICES.keys()))

# =========================
# FETCH LIVE DATA
# =========================
data = get_option_chain(index)

if not data:
    st.error("NSE fetch failed")
    st.stop()

signal = generate_signal()

if signal:
    option, strike, spot = get_atm_option(data, signal)

    opt_type = "CE" if "CE" in signal else "PE"

    symbol = build_symbol(index, strike, opt_type)

    entry = option.get("lastPrice", 0)

    target = entry + 45
    sl = entry - 12

    qty = position_size(index)

    st.markdown(f"""
    ### ⚡ {signal}
    Spot: ₹{spot}  
    Strike: {strike}  
    Premium: ₹{entry}  
    Target: ₹{target}  
    SL: ₹{sl}  
    Qty: {qty}  
    Symbol: {symbol}
    """)

    if mode == "AUTO" and auto_ok:
        result = place_order(symbol, qty)
        st.success(result)
    else:
        st.info("Manual Mode")

else:
    st.info("No Signal")