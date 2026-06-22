from dataclasses import asdict
import pandas as pd

from core.indicators import add_indicators
from core.strategy_base import Signal
from core.config import StrategyConfig
from core.signals import calc_trailing_stop

def ema_vwap_crossover(df: pd.DataFrame, cfg: StrategyConfig) -> dict:
    data = add_indicators(df, cfg.ema_fast, cfg.ema_slow)
    if len(data) < 2:
        return asdict(Signal(signal="WAIT", side="NONE", action="NONE", reason="Not enough candles", strategy_name=cfg.name))

    prev = data.iloc[-2]
    last = data.iloc[-1]

    bullish = prev["ema_fast"] <= prev["ema_slow"] and last["ema_fast"] > last["ema_slow"] and last["close"] > last["vwap"]
    bearish = prev["ema_fast"] >= prev["ema_slow"] and last["ema_fast"] < last["ema_slow"] and last["close"] < last["vwap"]

    entry = float(last["close"])

    if bullish:
        base_sl = entry - cfg.sl_points
        trail_sl = calc_trailing_stop(entry, entry, base_sl, cfg.trail_after_points, cfg.trail_step_points)
        return asdict(Signal(
            signal="BUY_CE",
            side="BUY",
            action="BUY_CE",
            reason="EMA crossover above VWAP",
            entry_price=entry,
            target_price=entry + cfg.target_points,
            stop_loss_price=base_sl,
            trailing_stop_price=trail_sl,
            confidence=85,
            timestamp=str(last["timestamp"]),
            strategy_name=cfg.name,
        ))

    if bearish:
        base_sl = entry - cfg.sl_points
        trail_sl = calc_trailing_stop(entry, entry, base_sl, cfg.trail_after_points, cfg.trail_step_points)
        return asdict(Signal(
            signal="BUY_PE",
            side="BUY",
            action="BUY_PE",
            reason="EMA crossover below VWAP",
            entry_price=entry,
            target_price=entry + cfg.target_points,
            stop_loss_price=base_sl,
            trailing_stop_price=trail_sl,
            confidence=85,
            timestamp=str(last["timestamp"]),
            strategy_name=cfg.name,
        ))

    return asdict(Signal(signal="WAIT", side="NONE", action="NONE", reason="No valid crossover", timestamp=str(last["timestamp"]), strategy_name=cfg.name))

STRATEGY_REGISTRY = {
    "EMA VWAP Crossover": ema_vwap_crossover,
}