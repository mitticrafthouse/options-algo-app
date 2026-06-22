from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional

import pandas as pd

from core.signals import generate_signal
from core.indicators import add_indicators


@dataclass
class TradeResult:
    entry_time: str
    exit_time: str
    signal: str
    entry: float
    exit: float
    pnl: float
    result: str
    bars_held: int
    mfe: float = 0.0
    mae: float = 0.0
    initial_sl: float = 0.0
    final_sl: float = 0.0
    scaled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _scaled_stop_price(entry: float, sl_pts: float, best_favorable_move: float, scale_after_pts: float, scale_factor: float) -> float:
    initial_sl = entry - sl_pts
    if best_favorable_move >= scale_after_pts:
        scaled_sl_pts = max(1.0, sl_pts * scale_factor)
        return entry - scaled_sl_pts
    return initial_sl


def _simulate_exit(
    candles: pd.DataFrame,
    start_idx: int,
    entry: float,
    target_pts: float,
    sl_pts: float,
    scale_after_pts: float = 0.0,
    scale_factor: float = 1.0,
) -> tuple[Optional[float], Optional[str], int, float, float, float, float, bool]:
    target = entry + target_pts
    initial_sl = entry - sl_pts
    final_sl = initial_sl

    max_fav = 0.0
    max_adv = 0.0
    scaled = False

    for i in range(start_idx + 1, len(candles)):
        row = candles.iloc[i]
        high = float(row["high"])
        low = float(row["low"])

        max_fav = max(max_fav, high - entry)
        max_adv = max(max_adv, entry - low)

        if not scaled and scale_after_pts > 0 and max_fav >= scale_after_pts:
            final_sl = _scaled_stop_price(entry, sl_pts, max_fav, scale_after_pts, scale_factor)
            scaled = True

        if low <= final_sl:
            return final_sl, "SL HIT", i - start_idx, max_fav, max_adv, initial_sl, final_sl, scaled
        if high >= target:
            return target, "TARGET", i - start_idx, max_fav, max_adv, initial_sl, final_sl, scaled

    return None, None, len(candles) - start_idx - 1, max_fav, max_adv, initial_sl, final_sl, scaled


def run_backtest(
    df: pd.DataFrame,
    target_pts: float = 45.0,
    sl_pts: float = 12.0,
    lot_size: int = 75,
    lots: int = 1,
    ema_fast: int = 9,
    ema_slow: int = 21,
    use_volume_filter: bool = True,
    one_trade_at_a_time: bool = True,
    scale_after_pts: float = 0.0,
    scale_factor: float = 1.0,
) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    data = add_indicators(df, ema_fast=ema_fast, ema_slow=ema_slow).reset_index(drop=True)
    results: List[TradeResult] = []
    i = max(ema_slow + 5, 25)

    while i < len(data) - 1:
        window = data.iloc[: i + 1].copy()
        sig = generate_signal(
            window,
            ema_fast=ema_fast,
            ema_slow=ema_slow,
            target_points=target_pts,
            sl_points=sl_pts,
            use_volume_filter=use_volume_filter,
        )

        if sig["signal"] not in ["BUY_CE", "BUY_PE"]:
            i += 1
            continue

        entry_idx = i
        entry_row = data.iloc[entry_idx]
        entry = float(entry_row["close"])

        exit_price, outcome, bars_held, mfe, mae, initial_sl, final_sl, scaled = _simulate_exit(
            data,
            entry_idx,
            entry,
            target_pts,
            sl_pts,
            scale_after_pts=scale_after_pts,
            scale_factor=scale_factor,
        )

        if exit_price is None:
            break

        qty = lot_size * lots
        pnl = (exit_price - entry) * qty

        results.append(
            TradeResult(
                entry_time=str(entry_row["timestamp"]),
                exit_time=str(data.iloc[entry_idx + bars_held]["timestamp"]),
                signal=sig["signal"],
                entry=entry,
                exit=exit_price,
                pnl=pnl,
                result=outcome or "OPEN",
                bars_held=bars_held,
                mfe=mfe,
                mae=mae,
                initial_sl=initial_sl,
                final_sl=final_sl,
                scaled=scaled,
            )
        )

        if one_trade_at_a_time:
            i = entry_idx + bars_held + 1
        else:
            i += 1

    out = pd.DataFrame([r.to_dict() for r in results])
    if out.empty:
        return out

    out["cum_pnl"] = out["pnl"].cumsum()
    out["win"] = out["result"].eq("TARGET")
    return out


def backtest_summary(trades: pd.DataFrame) -> Dict[str, Any]:
    if trades is None or trades.empty:
        return {
            "trades": 0,
            "win_rate": 0.0,
            "net_pnl": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "profit_factor": 0.0,
            "avg_pnl": 0.0,
            "max_win": 0.0,
            "max_loss": 0.0,
        }

    net_pnl = float(trades["pnl"].sum())
    gross_profit = float(trades.loc[trades["pnl"] > 0, "pnl"].sum())
    gross_loss = float(abs(trades.loc[trades["pnl"] < 0, "pnl"].sum()))
    profit_factor = (gross_profit / gross_loss) if gross_loss else float("inf")
    win_rate = float((trades["result"] == "TARGET").mean() * 100)
    avg_pnl = float(trades["pnl"].mean())
    max_win = float(trades["pnl"].max())
    max_loss = float(trades["pnl"].min())

    return {
        "trades": int(len(trades)),
        "win_rate": win_rate,
        "net_pnl": net_pnl,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
        "avg_pnl": avg_pnl,
        "max_win": max_win,
        "max_loss": max_loss,
    }