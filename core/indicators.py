import pandas as pd

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def vwap(df: pd.DataFrame) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3
    pv = tp * df["volume"]
    return pv.cumsum() / df["volume"].cumsum()

def add_indicators(df: pd.DataFrame, ema_fast: int = 9, ema_slow: int = 21) -> pd.DataFrame:
    out = df.copy()
    out["ema_fast"] = ema(out["close"], ema_fast)
    out["ema_slow"] = ema(out["close"], ema_slow)
    out["vwap"] = vwap(out)
    return out