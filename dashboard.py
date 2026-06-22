from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    go = None
    PLOTLY_AVAILABLE = False

from core.backtest import run_backtest, backtest_summary
from core.signals import generate_signal, classify_signal_for_mode
from core.indicators import ema, vwap
from core.config import LOT_SIZES


def sample_candles():
    data = [
        ["2026-06-19 09:15", 23500, 23520, 23490, 23510, 120000],
        ["2026-06-19 09:20", 23510, 23540, 23500, 23530, 135000],
        ["2026-06-19 09:25", 23530, 23545, 23505, 23515, 140000],
        ["2026-06-19 09:30", 23515, 23535, 23495, 23525, 150000],
        ["2026-06-19 09:35", 23525, 23560, 23520, 23550, 160000],
        ["2026-06-19 09:40", 23550, 23572, 23535, 23568, 175000],
        ["2026-06-19 09:45", 23568, 23605, 23560, 23598, 182000],
        ["2026-06-19 09:50", 23598, 23620, 23570, 23612, 190000],
        ["2026-06-19 09:55", 23612, 23618, 23585, 23592, 165000],
        ["2026-06-19 10:00", 23592, 23605, 23570, 23578, 158000],
        ["2026-06-19 10:05", 23578, 23600, 23565, 23595, 171000],
        ["2026-06-19 10:10", 23595, 23628, 23590, 23622, 188000],
        ["2026-06-19 10:15", 23622, 23644, 23605, 23633, 193000],
        ["2026-06-19 10:20", 23633, 23650, 23612, 23645, 201000],
        ["2026-06-19 10:25", 23645, 23670, 23625, 23662, 210000],
    ]
    return pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])


def _make_trade_chart(candles: pd.DataFrame, trades: pd.DataFrame):
    candles = candles.copy()
    candles["timestamp"] = pd.to_datetime(candles["timestamp"])

    candles["ema9"] = ema(candles["close"], 9)
    candles["ema21"] = ema(candles["close"], 21)
    candles["vwap"] = vwap(candles)

    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=candles["timestamp"],
            open=candles["open"],
            high=candles["high"],
            low=candles["low"],
            close=candles["close"],
            name="OHLC",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=candles["timestamp"],
            y=candles["ema9"],
            mode="lines",
            name="EMA 9",
            line=dict(color="#00e5ff", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=candles["timestamp"],
            y=candles["ema21"],
            mode="lines",
            name="EMA 21",
            line=dict(color="#7c4dff", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=candles["timestamp"],
            y=candles["vwap"],
            mode="lines",
            name="VWAP",
            line=dict(color="#ffd740", width=2, dash="dot"),
        )
    )

    if trades is not None and not trades.empty:
        trades = trades.copy()
        trades["entry_time"] = pd.to_datetime(trades["entry_time"])
        trades["exit_time"] = pd.to_datetime(trades["exit_time"])

        fig.add_trace(
            go.Scatter(
                x=trades["entry_time"],
                y=trades["entry"],
                mode="markers+text",
                name="Entries",
                marker=dict(color="#00e676", size=12, symbol="triangle-up"),
                text=trades["signal"],
                textposition="top center",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=trades["exit_time"],
                y=trades["exit"],
                mode="markers+text",
                name="Exits",
                marker=dict(
                    color=["#00e676" if x > 0 else "#ff1744" for x in trades["pnl"]],
                    size=11,
                    symbol="x",
                ),
                text=trades["result"],
                textposition="bottom center",
            )
        )

    fig.update_layout(
        template="plotly_dark",
        height=650,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h"),
        title="Backtest Chart with Trades",
        xaxis_title="Time",
        yaxis_title="Price",
    )
    return fig


def render_dashboard(mode, index, opt_type, strike, entry_premium, target_pts, sl_pts, lots):
    st.title("Options Scalper Dashboard")
    st.caption("Live signal engine with AUTO / MANUAL / BACKTEST support")

    qty = LOT_SIZES[index] * lots
    target_px = entry_premium + target_pts
    sl_px = entry_premium - sl_pts

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Quantity", qty)
    c2.metric("Target", f"₹{target_px:.0f}")
    c3.metric("Stop Loss", f"₹{sl_px:.0f}")
    c4.metric("Lot Size", LOT_SIZES[index])

    left, right = st.columns([1.15, 0.85])

    with left:
        st.subheader("Signal Panel")
        candles = sample_candles()
        sig = generate_signal(
            candles,
            target_points=target_pts,
            sl_points=sl_pts,
            use_volume_filter=True,
        )
        sig = classify_signal_for_mode(sig, mode)

        if sig["signal"] == "BUY_CE":
            st.success(f"BUY CE: {sig['reason']}")
        elif sig["signal"] == "BUY_PE":
            st.error(f"BUY PE: {sig['reason']}")
        else:
            st.info(sig["reason"])

        st.write(f"Mode: **{mode}**")
        st.write(f"Index: **{index}**")
        st.write(f"Option: **{opt_type}**")
        st.write(f"Strike: **{strike}**")
        st.write(f"Entry premium: **₹{entry_premium:.0f}**")
        st.write(f"Target: **₹{target_px:.0f}**")
        st.write(f"Stop loss: **₹{sl_px:.0f}**")
        st.write(f"Qty: **{qty}**")

    with right:
        st.subheader("Config Preview")
        st.code(
            f'''INDEX = "{index}"
MODE = "{mode}"
OPTION_TYPE = "{opt_type}"
STRIKE = {strike}
ENTRY_PREMIUM = {entry_premium}
TARGET_POINTS = {target_pts}
SL_POINTS = {sl_pts}
LOTS = {lots}
LOT_SIZE = {LOT_SIZES[index]}''',
            language="python",
        )

    st.divider()

    tab1, tab2, tab3 = st.tabs(["Live / Backtest", "Trade Log", "Order Panel"])

    with tab1:
        st.subheader("Backtest Controls")
        bt_target = st.number_input("Backtest Target Points", value=float(target_pts), step=1.0, key="bt_target")
        bt_sl = st.number_input("Backtest Stop Loss Points", value=float(sl_pts), step=1.0, key="bt_sl")
        bt_scale_after = st.number_input("Scale SL after favorable move", value=20.0, step=1.0, key="bt_scale_after")
        bt_scale_factor = st.number_input("Scale factor", value=0.5, min_value=0.1, max_value=1.0, step=0.1, key="bt_scale_factor")

        run_btn = st.button("Run Backtest", type="primary")

        if run_btn:
            trades = run_backtest(
                candles,
                target_pts=bt_target,
                sl_pts=bt_sl,
                lot_size=LOT_SIZES[index],
                lots=lots,
                scale_after_pts=bt_scale_after,
                scale_factor=bt_scale_factor,
            )

            summary = backtest_summary(trades)

            a, b, c, d = st.columns(4)
            a.metric("Trades", summary["trades"])
            b.metric("Win Rate", f"{summary['win_rate']:.0f}%")
            c.metric("Net P&L", f"₹{summary['net_pnl']:,.0f}")
            d.metric(
                "Profit Factor",
                f"{summary['profit_factor']:.2f}" if summary["profit_factor"] != float("inf") else "∞",
            )

            st.dataframe(trades, use_container_width=True, hide_index=True)

            if not trades.empty:
                if PLOTLY_AVAILABLE:
                    try:
                        fig = _make_trade_chart(candles, trades)
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.warning(f"Chart could not be rendered: {e}")
                        st.dataframe(trades, use_container_width=True, hide_index=True)
                else:
                    st.warning("Plotly is not installed in this environment. Showing table only.")
                    st.dataframe(trades, use_container_width=True, hide_index=True)

                output_dir = Path("output")
                output_dir.mkdir(exist_ok=True)
                csv_path = output_dir / "backtest_results.csv"
                trades.to_csv(csv_path, index=False)

                st.download_button(
                    "Download CSV",
                    data=trades.to_csv(index=False).encode("utf-8"),
                    file_name="backtest_results.csv",
                    mime="text/csv",
                )
                st.success(f"CSV saved to {csv_path}")

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
        st.write(f"Win Rate: {(trade_log['P&L'] > 0).mean() * 100:.0f}%")
        st.write(f"Trades: {len(trade_log)}")

    with tab3:
        st.subheader("Place Order Preview")
        st.json(
            {
                "mode": mode,
                "index": index,
                "option_type": opt_type,
                "strike": strike,
                "quantity": qty,
                "entry_premium": entry_premium,
                "target": target_px,
                "stop_loss": sl_px,
            }
        )
        st.warning("Connect this section to the Dhan order API in AUTO mode after live signal confirmation.")