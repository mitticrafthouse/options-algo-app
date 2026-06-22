from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

import pandas as pd

from core.indicators import add_indicators


@dataclass
class SignalResult:
    signal: str
    side: str
    action: str
    reason: str
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    confidence: int = 0
    trend: str = "NEUTRAL"
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _last_two(df: pd.DataFrame):
    if len(df) < 2:
        return None, None
    return df.iloc[-2], df.iloc[-1]


def _volume_confirmation(row: pd.Series, lookback: pd.DataFrame) -> bool:
    if "volume" not in lookback.columns:
        return False
    avg_vol = lookback["volume"].tail(20).mean()
    if pd.isna(avg_vol) or avg_vol <= 0:
        return False
    return float(row["volume"]) >= float(avg_vol)


def generate_signal(
    df: pd.DataFrame,
    ema_fast: int = 9,
    ema_slow: int = 21,
    target_points: float = 45.0,
    sl_points: float = 12.0,
    use_volume_filter: bool = True,
) -> Dict[str, Any]:
    data = add_indicators(df, ema_fast=ema_fast, ema_slow=ema_slow)
    prev, last = _last_two(data)

    if prev is None or last is None:
        return SignalResult(
            signal="WAIT",
            side="NONE",
            action="NONE",
            reason="Not enough candles",
        ).to_dict()

    bullish_cross = (
        prev["ema_fast"] <= prev["ema_slow"]
        and last["ema_fast"] > last["ema_slow"]
        and last["close"] > last["vwap"]
    )

    bearish_cross = (
        prev["ema_fast"] >= prev["ema_slow"]
        and last["ema_fast"] < last["ema_slow"]
        and last["close"] < last["vwap"]
    )

    vol_ok = True
    if use_volume_filter:
        vol_ok = _volume_confirmation(last, data)

    trend = "BULLISH" if last["close"] > last["vwap"] else "BEARISH" if last["close"] < last["vwap"] else "NEUTRAL"

    if bullish_cross and vol_ok:
        entry = float(last["close"])
        return SignalResult(
            signal="BUY_CE",
            side="BUY",
            action="BUY_CE",
            reason="EMA fast crossed above EMA slow with price above VWAP and volume confirmation",
            entry_price=entry,
            target_price=entry + float(target_points),
            stop_loss_price=entry - float(sl_points),
            confidence=85,
            trend=trend,
            timestamp=str(last["timestamp"]),
        ).to_dict()

    if bearish_cross and vol_ok:
        entry = float(last["close"])
        return SignalResult(
            signal="BUY_PE",
            side="BUY",
            action="BUY_PE",
            reason="EMA fast crossed below EMA slow with price below VWAP and volume confirmation",
            entry_price=entry,
            target_price=entry + float(target_points),
            stop_loss_price=entry - float(sl_points),
            confidence=85,
            trend=trend,
            timestamp=str(last["timestamp"]),
        ).to_dict()

    reason = "VWAP/EMA condition not confirmed"
    if bullish_cross and not vol_ok:
        reason = "Bullish crossover found, but volume confirmation failed"
    elif bearish_cross and not vol_ok:
        reason = "Bearish crossover found, but volume confirmation failed"

    return SignalResult(
        signal="WAIT",
        side="NONE",
        action="NONE",
        reason=reason,
        confidence=40 if (bullish_cross or bearish_cross) else 20,
        trend=trend,
        timestamp=str(last["timestamp"]),
    ).to_dict()


def classify_signal_for_mode(signal: Dict[str, Any], mode: str) -> Dict[str, Any]:
    out = dict(signal)
    mode = (mode or "").upper()

    if mode == "AUTO" and signal.get("signal") in ["BUY_CE", "BUY_PE"]:
        out["execution"] = "PLACE_ORDER"
    elif mode == "MANUAL" and signal.get("signal") in ["BUY_CE", "BUY_PE"]:
        out["execution"] = "SHOW_ONLY"
    else:
        out["execution"] = "NO_ACTION"

    out["mode"] = mode
    return out
