from __future__ import annotations

import pandas as pd


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    required = ["timestamp", "open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    out = df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"])
    out = out.sort_values("timestamp").reset_index(drop=True)

    for col in ["open", "high", "low", "close", "volume"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out = out.dropna(subset=["open", "high", "low", "close", "volume"])
    return out


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def vwap(df: pd.DataFrame) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    pv = tp * df["volume"]
    return pv.cumsum() / df["volume"].cumsum()


def candle_body(df: pd.DataFrame) -> pd.Series:
    return df["close"] - df["open"]


def candle_range(df: pd.DataFrame) -> pd.Series:
    return df["high"] - df["low"]


def average_true_range(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            (df["high"] - df["low"]).abs(),
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window=period, min_periods=period).mean()


def add_indicators(
    df: pd.DataFrame,
    ema_fast: int = 9,
    ema_slow: int = 21,
    atr_period: int = 14,
) -> pd.DataFrame:
    out = normalize_ohlcv(df)
    out["ema_fast"] = ema(out["close"], ema_fast)
    out["ema_slow"] = ema(out["close"], ema_slow)
    out["vwap"] = vwap(out)
    out["atr"] = average_true_range(out, atr_period)
    out["body"] = candle_body(out)
    out["range"] = candle_range(out)
    out["bullish"] = out["close"] > out["open"]
    out["bearish"] = out["close"] < out["open"]
    return out