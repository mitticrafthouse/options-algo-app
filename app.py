from __future__ import annotations

import streamlit as st

from core.auth import is_authenticated, logout
from ui.login import render_login
from ui.dashboard import render_dashboard
from core.config import (
    INDEX_LIST,
    OPTION_TYPES,
    MODES,
    DEFAULT_TARGET_POINTS,
    DEFAULT_SL_POINTS,
    DEFAULT_LOTS,
)

st.set_page_config(
    page_title="Options Scalper Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if "username" not in st.session_state:
    st.session_state["username"] = ""

if not is_authenticated():
    render_login()
    st.stop()

st.sidebar.title("Trading Control")

st.sidebar.caption(f"Logged in as: {st.session_state.get('username', 'trader')}")

if st.sidebar.button("Logout"):
    logout()

st.sidebar.divider()

mode = st.sidebar.radio("Mode", MODES, horizontal=True)
index = st.sidebar.radio("Index", INDEX_LIST, horizontal=True)
opt_type = st.sidebar.selectbox("Option Type", OPTION_TYPES)

strike = st.sidebar.number_input("Strike", value=23500, step=50)
entry_premium = st.sidebar.number_input("Entry Premium", value=110.0, step=1.0)
target_pts = st.sidebar.number_input("Target Points", value=float(DEFAULT_TARGET_POINTS), step=1.0)
sl_pts = st.sidebar.number_input("Stop Loss Points", value=float(DEFAULT_SL_POINTS), step=1.0)
lots = st.sidebar.number_input("Lots", value=int(DEFAULT_LOTS), min_value=1, step=1)

st.sidebar.divider()
st.sidebar.subheader("Backtest Controls")
st.sidebar.caption("These controls are used inside the backtest tab.")
st.session_state["bt_target_pts"] = st.sidebar.number_input(
    "BT Target Points",
    value=float(target_pts),
    step=1.0,
)
st.session_state["bt_sl_pts"] = st.sidebar.number_input(
    "BT Stop Loss Points",
    value=float(sl_pts),
    step=1.0,
)
st.session_state["bt_scale_after"] = st.sidebar.number_input(
    "Scale SL after favorable move",
    value=20.0,
    step=1.0,
)
st.session_state["bt_scale_factor"] = st.sidebar.number_input(
    "Scale factor",
    value=0.5,
    min_value=0.1,
    max_value=1.0,
    step=0.1,
)

render_dashboard(
    mode=mode,
    index=index,
    opt_type=opt_type,
    strike=strike,
    entry_premium=entry_premium,
    target_pts=target_pts,
    sl_pts=sl_pts,
    lots=lots,
)