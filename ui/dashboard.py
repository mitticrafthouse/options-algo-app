from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    go = None
    PLOTLY_AVAILABLE = False

from core.backtest import run_backtest, backtest_summary
from core.config import INSTRUMENTS, MODES, StrategyConfig
from core.market_hours import market_is_open
from core.nse_data import get_live_lot_size
from core.risk import required_capital
from core.signals import build_order_payload, build_signal_text, calc_trailing_stop
from core.strategies import STRATEGY_REGISTRY
from services.broker import get_dhan_balance, place_order_if_funds_ok

IST = ZoneInfo("Asia/Kolkata")


def sample_candles():
    data = [
        ["2026-06-22 09:15", 23500, 23520, 23490, 23510, 120000],
        ["2026-06-22 09:20", 23510, 23540, 23500, 23530, 135000],
        ["2026-06-22 09:25", 23530, 23545, 23505, 23515, 140000],
        ["2026-06-22 09:30", 23515, 23535, 23495, 23525, 150000],
        ["2026-06-22 09:35", 23525, 23560, 23520, 23550, 160000],
        ["2026-06-22 09:40", 23550, 23572, 23535, 23568, 175000],
        ["2026-06-22 09:45", 23568, 23605, 23560, 23598, 182000],
        ["2026-06-22 09:50", 23598, 23620, 23570, 23612, 190000],
        ["2026-06-22 09:55", 23612, 23618, 23585, 23592, 165000],
        ["2026-06-22 10:00", 23592, 23605, 23570, 23578, 158000],
        ["2026-06-22 10:05", 23578, 23600, 23565, 23595, 171000],
        ["2026-06-22 10:10", 23595, 23628, 23590, 23622, 188000],
        ["2026-06-22 10:15", 23622, 23644, 23605, 23633, 193000],
        ["2026-06-22 10:20", 23633, 23650, 23612, 23645, 201000],
        ["2026-06-22 10:25", 23645, 23670, 23625, 23662, 210000],
        ["2026-06-22 10:30", 23662, 23688, 23640, 23679, 215000],
        ["2026-06-22 10:35", 23679, 23705, 23655, 23698, 220000],
    ]
    return pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])


def _make_trade_chart(candles: pd.DataFrame, trades: pd.DataFrame):
    candles = candles.copy()
    candles["timestamp"] = pd.to_datetime(candles["timestamp"])
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


def _init_state():
    defaults = {
        "mode": "AUTO",
        "instrument": "NIFTY",
        "selected_strategy": next(iter(STRATEGY_REGISTRY)),
        "client_id": "",
        "access_token": "",
        "balance": None,
        "live_order_status": "",
        "active_trade": None,
        "last_trail_sl": None,
        "last_order_id": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _trail_stop_tick(entry: float, high_seen: float, base_sl: float, trail_after: float, trail_step: float) -> float:
    return calc_trailing_stop(
        current_price=high_seen,
        entry_price=entry,
        current_sl=base_sl,
        trail_after_points=trail_after,
        trail_step_points=trail_step,
    )


def render_dashboard():
    _init_state()

    st.title("Options Scalper Pro")
    st.caption("Multi-strategy live scanner for NIFTY, BANKNIFTY, FINNIFTY, and SENSEX")

    top1, top2, top3, top4 = st.columns(4)
    top1.selectbox("Mode", MODES, index=MODES.index(st.session_state.mode), key="mode")
    top2.selectbox("Index", INSTRUMENTS, index=INSTRUMENTS.index(st.session_state.instrument), key="instrument")
    top3.selectbox(
        "Strategy",
        list(STRATEGY_REGISTRY.keys()),
        index=list(STRATEGY_REGISTRY.keys()).index(st.session_state.selected_strategy),
        key="selected_strategy",
    )
    top4.metric("Market", "OPEN" if market_is_open() else "CLOSED")

    broker1, broker2 = st.columns(2)
    with broker1:
        st.session_state.client_id = st.text_input("Dhan Client ID", value=st.session_state.client_id)
    with broker2:
        st.session_state.access_token = st.text_input(
            "Dhan Access Token",
            value=st.session_state.access_token,
            type="password",
        )

    lot_size = get_live_lot_size(st.session_state.instrument)
    st.metric("Live Lot Size", lot_size)

    balance = None
    if st.session_state.access_token:
        balance = get_dhan_balance(st.session_state.access_token)
        st.session_state.balance = balance
        if balance is not None:
            st.metric("Dhan Balance", f"₹{balance:,.0f}")
        else:
            st.warning("Unable to fetch live Dhan balance.")

    if not market_is_open():
        st.info("Market is closed. Signals are shown for review only.")

    candles = sample_candles()
    cfg = StrategyConfig(name=st.session_state.selected_strategy, instrument=st.session_state.instrument)
    sig = STRATEGY_REGISTRY[st.session_state.selected_strategy](candles, cfg)

    if sig["signal"] in ["BUY_CE", "BUY_PE"]:
        expiry = "23Jun2026"
        opt_type = "CE" if sig["signal"] == "BUY_CE" else "PE"
        entry = float(sig["entry_price"])
        sl = float(sig["stop_loss_price"])
        target = float(sig["target_price"])
        qty = int(lot_size)

        signal_text = build_signal_text(
            st.session_state.instrument,
            expiry,
            opt_type,
            entry,
            sl,
            target,
            qty=qty,
        )

        st.success(signal_text)
        st.code(signal_text)

        trail_after = float(cfg.trail_after_points)
        trail_step = float(cfg.trail_step_points)
        high_seen = float(candles["high"].iloc[-1])
        trailing_sl = _trail_stop_tick(entry, high_seen, sl, trail_after, trail_step)

        c1, c2, c3 = st.columns(3)
        c1.metric("Initial SL", f"{sl:.0f}")
        c2.metric("Trailing SL", f"{trailing_sl:.0f}")
        c3.metric("Target", f"{target:.0f}")

        st.session_state.active_trade = {
            "entry": entry,
            "sl": sl,
            "trail_sl": trailing_sl,
            "trail_after": trail_after,
            "trail_step": trail_step,
            "side": sig["signal"],
            "high_seen": high_seen,
        }

        order_payload = build_order_payload(
            index=st.session_state.instrument,
            opt_type=opt_type,
            strike=0,
            qty_lots=1,
            entry=entry,
            sl=trailing_sl,
            target=target,
        )
        required_margin = required_capital(entry_price=entry, lot_size=lot_size, lots=1)

        if market_is_open() and st.session_state.mode == "AUTO":
            if balance is None:
                st.error("Unable to fetch Dhan balance. AUTO mode blocked.", icon="🚨")
                st.session_state.mode = "MANUAL"
            elif balance < required_margin:
                st.error(
                    f"Insufficient balance. Available ₹{balance:,.0f}, required ₹{required_margin:,.0f}.",
                    icon="🚨",
                )
                st.session_state.mode = "MANUAL"
                st.warning("AUTO mode switched to MANUAL because balance is insufficient.")
            else:
                if st.button("Execute AUTO Order"):
                    result = place_order_if_funds_ok(
                        client_id=st.session_state.client_id,
                        access_token=st.session_state.access_token,
                        order_payload=order_payload,
                        required_margin=required_margin,
                    )
                    if not result["ok"]:
                        st.error(result["message"], icon="🚨")
                        st.session_state.mode = "MANUAL"
                    else:
                        st.success("Order sent to Dhan.")
                        st.session_state.live_order_status = result["status"]

        if st.session_state.active_trade:
            st.subheader("Trailing Stop Monitor")
            live_high = st.number_input(
                "Current/Observed High",
                value=float(st.session_state.active_trade["high_seen"]),
                step=1.0,
            )
            new_trail_sl = _trail_stop_tick(
                entry=float(st.session_state.active_trade["entry"]),
                high_seen=float(live_high),
                base_sl=float(st.session_state.active_trade["sl"]),
                trail_after=float(st.session_state.active_trade["trail_after"]),
                trail_step=float(st.session_state.active_trade["trail_step"]),
            )

            st.write(f"Current trailing SL: {new_trail_sl:.0f}")

            if st.session_state.last_trail_sl is None:
                st.session_state.last_trail_sl = new_trail_sl

            if new_trail_sl > float(st.session_state.last_trail_sl):
                st.session_state.last_trail_sl = new_trail_sl
                st.success(f"Trailing SL updated to {new_trail_sl:.0f}")

                if st.session_state.mode == "AUTO" and st.session_state.access_token and st.session_state.last_order_id:
                    from services.broker import modify_order
                    resp = modify_order(
                        st.session_state.access_token,
                        st.session_state.last_order_id,
                        trigger_price=new_trail_sl,
                        price=0.0,
                    )
                    if resp.get("status") == "ERROR":
                        st.error(f"Unable to modify order: {resp.get('message', 'Unknown error')}", icon="🚨")
                    else:
                        st.info("Broker order modified with updated trailing SL.")
        else:
            st.info("No active trade to trail yet.")
    else:
        st.warning(sig["reason"])

    st.divider()

    st.subheader("Strategy Output")
    st.json(sig)

    st.subheader("Candles")
    st.dataframe(candles, use_container_width=True, hide_index=True)

    st.subheader("Backtest")
    trades = run_backtest(candles, lot_size=lot_size, lots=1)
    summary = backtest_summary(trades)

    a, b, c, d = st.columns(4)
    a.metric("Trades", summary["trades"])
    b.metric("Win Rate", f"{summary['win_rate']:.0f}%")
    c.metric("Net P&L", f"₹{summary['net_pnl']:,.0f}")
    d.metric("Profit Factor", f"{summary['profit_factor']:.2f}" if summary["profit_factor"] != float("inf") else "∞")

    if not trades.empty:
        st.dataframe(trades, use_container_width=True, hide_index=True)
        if PLOTLY_AVAILABLE:
            st.plotly_chart(_make_trade_chart(candles, trades), use_container_width=True)

        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        trades.to_csv(output_dir / "backtest_results.csv", index=False)