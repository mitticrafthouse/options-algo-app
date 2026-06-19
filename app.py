import streamlit as st
import pandas as pd
from pathlib import Path
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Options Scalper Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #0a0d14 0%, #111620 100%);
        color: #e8edf5;
    }
    .block-container {
        padding-top: 1.0rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }
    .panel {
        background: #161d2e;
        border: 1px solid #1e2a42;
        border-radius: 14px;
        padding: 18px 20px;
    }
    .small {
        color: #6b7a96;
        font-size: 13px;
    }
    .headline {
        font-size: 26px;
        font-weight: 800;
        line-height: 1.15;
        margin-bottom: 0.15rem;
    }
    .subheadline {
        color: #6b7a96;
        font-size: 13px;
        margin-bottom: 0.6rem;
    }
    .signal-bull { color: #00e676; font-weight: 800; }
    .signal-bear { color: #ff1744; font-weight: 800; }
    .signal-neutral { color: #00e5ff; font-weight: 800; }
    .codebox {
        background: #0a0d14;
        border: 1px solid #1e2a42;
        border-radius: 10px;
        padding: 14px;
        font-family: monospace;
        white-space: pre-wrap;
        color: #e8edf5;
        font-size: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

def lot_size(index: str) -> int:
    return 75 if index == "NIFTY" else 20

def calc_pnl(index, lots, entry, target_pts, sl_pts):
    ls = lot_size(index)
    qty = ls * lots
    max_profit = target_pts * qty
    max_loss = sl_pts * qty
    capital = entry * qty
    roi = (max_profit / capital * 100) if capital else 0
    exit_px = entry + target_pts
    sl_exit = entry - sl_pts
    rr = (target_pts / sl_pts) if sl_pts else 0
    win_needed = round(100 / (1 + rr)) if rr else 50
    risk_pct = (max_loss / capital * 100) if capital else 0
    return qty, max_profit, max_loss, capital, roi, exit_px, sl_exit, rr, win_needed, risk_pct

def build_config(index, mode, target_pts, sl_pts, lots):
    return f'''# ── Core settings ──────────────────
CLIENT_ID = "YOUR_CLIENT_ID"
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"

INDEX = "{index}"
MODE = "{mode}"

# ── Strategy ───────────────────────
TARGET_POINTS = {int(target_pts)}
SL_POINTS = {int(sl_pts)}
LOTS = {int(lots)}
LOT_SIZE = {lot_size(index)}  # Nifty=75
EMA_FAST = 9
EMA_SLOW = 21

# ── Square-off time ────────────────
SQUAREOFF_HOUR = 15
SQUAREOFF_MINUTE = 15
MAX_TRADES = 3
'''

def build_signal_text(mode, index, strike, opt_type, entry, target, sl, qty, lots):
    return (
        f"⚡ {mode} TRADE SIGNAL\n"
        f"BUY {index} {strike} {opt_type}\n"
        f"Entry: ₹{entry:.0f}\n"
        f"Target: ₹{target:.0f}\n"
        f"SL: ₹{sl:.0f}\n"
        f"Qty: {qty} ({lots} lot{'s' if lots > 1 else ''})"
    )

st.sidebar.title("Configuration")
mode = st.sidebar.radio("Mode", ["AUTO", "MANUAL"], horizontal=True)
index = st.sidebar.radio("Index", ["NIFTY", "SENSEX"], horizontal=True)
opt_type = st.sidebar.selectbox("Option Type", ["CE", "PE"])
strike = st.sidebar.number_input("Strike", value=23500, step=50)
entry = st.sidebar.number_input("Entry Premium", value=110.0, step=1.0)
target_pts = st.sidebar.number_input("Target Points", value=45.0, step=1.0)
sl_pts = st.sidebar.number_input("Stop Loss Points", value=12.0, step=1.0)
lots = st.sidebar.number_input("Lots", value=1, min_value=1, step=1)

qty, max_profit, max_loss, capital, roi, exit_px, sl_exit, rr, win_needed, risk_pct = calc_pnl(
    index, lots, entry, target_pts, sl_pts
)

st.markdown('<div class="headline">Options Scalper Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="subheadline">EMA 9 / EMA 21 crossover + VWAP confirmation · 5-min candles</div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Quantity", f"{qty}")
col2.metric("Max Profit", f"₹{max_profit:,.0f}")
col3.metric("Max Loss", f"₹{max_loss:,.0f}")
col4.metric("Risk:Reward", f"1 : {rr:.1f}")

st.write("")

left, right = st.columns([1.1, 0.9])

with left:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Live Signal Output")
    signal_class = "signal-bull" if opt_type == "CE" else "signal-bear"
    st.markdown(
        f"<div class='{signal_class}' style='font-size:22px;'>"
        f"{'BULLISH' if opt_type == 'CE' else 'BEARISH'} SIGNAL</div>",
        unsafe_allow_html=True,
    )
    st.write(f"**{index} {strike} {opt_type} @ ₹{entry:.0f}**")
    st.write(f"Spot: **23,487**")
    st.write(f"Entry Premium: **₹{entry:.0f}**")
    st.write(f"Target Exit: **₹{exit_px:.0f}**")
    st.write(f"Stop Loss: **₹{sl_exit:.0f}**")
    st.write(f"Qty / Lots: **{qty}**")
    st.write(f"Est. Profit: **₹{max_profit:,.0f}**")
    st.info("This section is ready to connect to your live signal engine.")
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Python Config")
    st.code(build_config(index, mode, target_pts, sl_pts, lots), language="python")
    st.markdown("</div>", unsafe_allow_html=True)

st.write("")

tab1, tab2, tab3 = st.tabs(["Order Preview", "Trade Log", "Embedded HTML"])

with tab1:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("AUTO / MANUAL Preview")
    st.write(build_signal_text(mode, index, strike, opt_type, entry, entry + target_pts, entry - sl_pts, qty, lots))
    st.markdown("</div>", unsafe_allow_html=True)

with tab2:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Today's Signal Log")
    trade_df = pd.DataFrame(
        [
            {"Time": "09:35", "Instrument": "NIFTY 23500 CE", "Entry": 118, "Exit": 163, "P&L": 3375, "Mode": "AUTO", "Result": "TARGET"},
            {"Time": "11:10", "Instrument": "NIFTY 23450 PE", "Entry": 95, "Exit": 83, "P&L": -900, "Mode": "MANUAL", "Result": "SL HIT"},
            {"Time": "13:45", "Instrument": "NIFTY 23500 CE", "Entry": 132, "Exit": 177, "P&L": 3375, "Mode": "AUTO", "Result": "TARGET"},
        ]
    )
    st.dataframe(trade_df, use_container_width=True, hide_index=True)
    st.write(f"Net P&L: **₹{trade_df['P&L'].sum():,.0f}**")
    st.write(f"Win Rate: **{(trade_df['P&L'] > 0).mean() * 100:.0f}%**")
    st.write(f"Trades: **{len(trade_df)}**")
    st.markdown("</div>", unsafe_allow_html=True)

with tab3:
    html_path = Path("assets/dashboard.html")
    if html_path.exists():
        components.html(html_path.read_text(encoding="utf-8"), height=1200, scrolling=True)
    else:
        st.warning("Put your HTML file at assets/dashboard.html to embed it here.")
