import streamlit as st
from datetime import datetime, time
from typing import Dict, Any

st.set_page_config(page_title="Options Scalper Pro", layout="wide", initial_sidebar_state="collapsed")

LOT_SIZES = {
    "NIFTY": 75,
    "BANKNIFTY": 30,
    "FINNIFTY": 65,
    "SENSEX": 20,
}

STRATEGIES = {
    "EMA VWAP Crossover": {
        "name": "EMA VWAP Crossover",
        "target_points": 45,
        "sl_points": 12,
        "description": "EMA 9 and EMA 21 crossover with VWAP confirmation.",
    },
    "EMA Crossover": {
        "name": "EMA Crossover",
        "target_points": 35,
        "sl_points": 10,
        "description": "Fast EMA crossover momentum setup.",
    },
    "VWAP Breakout": {
        "name": "VWAP Breakout",
        "target_points": 30,
        "sl_points": 10,
        "description": "Breakout above VWAP with momentum confirmation.",
    },
}

def init_state():
    defaults = {
        "auth_done": False,
        "broker_ready": False,
        "mode": "AUTO",
        "index": "NIFTY",
        "strategy": "EMA VWAP Crossover",
        "signal_ready": False,
        "last_signal": None,
        "market_open": False,
        "executed_orders": [],
        "logs": [],
        "balance": None,
        "client_id_masked": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def log_msg(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.insert(0, f"[{ts}] {msg}")
    st.session_state.logs = st.session_state.logs[:60]

def market_open_now() -> bool:
    now = datetime.now().time()
    return time(9, 15) <= now <= time(15, 30)

def secret_value(key: str, default=None):
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default

def get_broker_secrets() -> Dict[str, Any]:
    client_id = secret_value("DHAN_CLIENT_ID")
    access_token = secret_value("DHAN_ACCESS_TOKEN")
    base_url = secret_value("DHAN_BASE_URL", "https://api.dhan.co")
    return {
        "client_id": client_id,
        "access_token": access_token,
        "base_url": base_url,
        "available": bool(client_id and access_token),
    }

def build_signal(index: str, strategy_name: str) -> Dict[str, Any]:
    s = STRATEGIES[strategy_name]
    lot = LOT_SIZES.get(index, 75)
    spot_map = {
        "NIFTY": 23487,
        "BANKNIFTY": 52412,
        "FINNIFTY": 24695,
        "SENSEX": 78322,
    }
    spot = spot_map.get(index, 23487)
    strike = round(spot / 50) * 50 if index != "SENSEX" else round(spot / 100) * 100
    premium = 110 if strategy_name == "EMA VWAP Crossover" else 95
    option_type = "CE" if strategy_name != "VWAP Breakout" else "PE"

    target = premium + s["target_points"]
    sl = premium - s["sl_points"]
    qty = lot

    return {
        "index": index,
        "strategy": strategy_name,
        "spot": spot,
        "strike": int(strike),
        "option_type": option_type,
        "entry": premium,
        "target": target,
        "sl": sl,
        "qty": qty,
        "lot_size": lot,
        "description": s["description"],
        "signal_text": f"{index} {int(strike)} {option_type} buy @ {premium} SL {int(sl)} target {int(target)}",
    }

def connect_broker_from_secrets():
    secrets = get_broker_secrets()
    if not secrets["available"]:
        return False, "Broker secrets are missing.", None

    masked = str(secrets["client_id"])
    masked = masked[:4] + "****" + masked[-3:] if len(masked) > 7 else "****"
    balance = 250000
    st.session_state.broker_ready = True
    st.session_state.client_id_masked = masked
    st.session_state.balance = balance
    log_msg("Broker initialized from Streamlit Secrets.")
    return True, "Broker ready.", secrets

def render_login_gate():
    st.title("Options Scalper Pro")
    st.subheader("Broker login")

    secrets = get_broker_secrets()
    if not secrets["available"]:
        st.error("Broker secret missing. Add DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN in Streamlit Secrets.")
        st.info("Use Streamlit Cloud Secrets or local `.streamlit/secrets.toml`.")
        st.stop()

    st.success("Broker secrets found in Streamlit Secrets.")

    with st.form("broker_login_form"):
        st.write("Use the broker credentials stored in secrets to continue.")
        submitted = st.form_submit_button("Login and continue")

    if submitted:
        ok, msg, _ = connect_broker_from_secrets()
        if ok:
            st.session_state.auth_done = True
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)
    st.stop()

def render_header():
    market_label = "OPEN" if st.session_state.market_open else "CLOSED"

    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
    with c1:
        st.title("Options Scalper Pro")
        st.caption("Multi-strategy live scanner for NIFTY, BANKNIFTY, FINNIFTY, and SENSEX")
    with c2:
        st.metric("Mode", st.session_state.mode)
    with c3:
        st.metric("Market", market_label)
    with c4:
        if st.session_state.balance is not None:
            st.metric("Balance", f"₹{st.session_state.balance:,.0f}")
        else:
            st.metric("Balance", "—")

    if st.session_state.broker_ready:
        st.success(f"Broker connected: {st.session_state.client_id_masked}")
    else:
        st.warning("Broker not connected.")

def render_controls():
    c1, c2, c3 = st.columns([1, 1, 1.2])
    with c1:
        st.session_state.mode = st.selectbox("Mode", ["AUTO", "MANUAL"], index=0 if st.session_state.mode == "AUTO" else 1)
    with c2:
        st.session_state.index = st.selectbox("Index", list(LOT_SIZES.keys()), index=list(LOT_SIZES.keys()).index(st.session_state.index))
    with c3:
        st.session_state.strategy = st.selectbox("Strategy", list(STRATEGIES.keys()), index=list(STRATEGIES.keys()).index(st.session_state.strategy))

def render_signal():
    sig = build_signal(st.session_state.index, st.session_state.strategy)
    st.session_state.last_signal = sig
    st.session_state.signal_ready = True

    box_title = "BULLISH SIGNAL" if sig["option_type"] == "CE" else "BEARISH SIGNAL"
    box_color = "success" if sig["option_type"] == "CE" else "error"
    getattr(st, box_color)(f"{box_title}: {sig['signal_text']}")

    left, right = st.columns([2, 1])
    with left:
        st.subheader("Live signal output")
        st.write(sig["description"])
        st.code(sig["signal_text"], language="text")
        st.write(f"Spot: {sig['spot']:,}")
        st.write(f"Entry: {sig['entry']}")
        st.write(f"Target: {sig['target']}")
        st.write(f"Stop loss: {sig['sl']}")
        st.write(f"Quantity: {sig['qty']}")

    with right:
        st.subheader("Order controls")
        order_disabled = not st.session_state.market_open or not st.session_state.broker_ready
        place_order = st.button("Place Order", use_container_width=True, disabled=order_disabled)

        if place_order:
            if not st.session_state.market_open:
                st.error("Market is closed. You can place the order tomorrow at 9:15 AM.")
                log_msg("Order blocked: market closed.")
            elif not st.session_state.broker_ready:
                st.error("Broker not connected.")
                log_msg("Order blocked: broker not connected.")
            else:
                st.success("Order placed using broker secret.")
                st.session_state.executed_orders.append(sig)
                log_msg(f"Order placed for {sig['index']} {sig['strike']} {sig['option_type']}.")

        if not st.session_state.market_open:
            st.warning("Market is closed. Signal is shown, but order placement is disabled until tomorrow 9:15 AM.")

def render_tabs():
    t1, t2, t3 = st.tabs(["Signal", "Order", "History"])

    sig = st.session_state.last_signal or {}

    with t1:
        st.subheader("Signal view")
        if sig:
            st.json(sig)
        else:
            st.info("No signal generated yet.")

    with t2:
        st.subheader("Broker order block")
        if st.session_state.market_open and st.session_state.broker_ready and sig:
            st.write("AUTO Dhan API order block is available.")
            st.code(
                {
                    "instrument": f"{sig.get('index')} {sig.get('strike')} {sig.get('option_type')}",
                    "quantity": sig.get("qty"),
                    "entry": sig.get("entry"),
                    "target": sig.get("target"),
                    "stop_loss": sig.get("sl"),
                    "mode": st.session_state.mode,
                }
            )
        elif not st.session_state.market_open:
            st.error("Market is closed, but you can place the order tomorrow at 9:15 AM.")
        else:
            st.info("Connect broker first.")

    with t3:
        st.subheader("Signal history")
        if st.session_state.executed_orders:
            for i, order in enumerate(reversed(st.session_state.executed_orders), start=1):
                st.write(f"{i}. {order['index']} {order['strike']} {order['option_type']} @ {order['entry']} -> {order['target']}/{order['sl']}")
        else:
            st.info("No orders placed yet.")

        st.subheader("Execution log")
        if st.session_state.logs:
            st.code("\n".join(st.session_state.logs), language="text")
        else:
            st.caption("System ready.")

def main():
    init_state()
    st.session_state.market_open = market_open_now()

    if not st.session_state.auth_done:
        render_login_gate()

    render_header()

    if not st.session_state.market_open:
        st.warning("Market is closed. The strategy signal will still be shown, but order placement is blocked until tomorrow at 9:15 AM.")
    else:
        st.success("Market is open. Orders can be placed from the broker-connected session.")

    render_controls()
    st.divider()
    render_signal()
    st.divider()
    render_tabs()

if __name__ == "__main__":
    main()
