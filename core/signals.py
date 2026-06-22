from __future__ import annotations

from typing import Dict, Any

from core.config import LOT_SIZES

def format_signal(index: str, expiry: str, opt_type: str, entry: float, sl: float, target: float) -> str:
    return f"{index} {expiry} {opt_type} buy @{entry:.0f} SL {sl:.0f} target {target:.0f}"

def build_order_payload(
    index: str,
    opt_type: str,
    strike: int,
    qty_lots: int,
    entry: float,
    sl: float,
    target: float,
) -> Dict[str, Any]:
    return {
        "instrument": index,
        "option_type": opt_type,
        "strike": strike,
        "quantity": qty_lots * LOT_SIZES[index],
        "entry": entry,
        "stop_loss": sl,
        "target": target,
    }

def build_signal_text(
    index: str,
    expiry: str,
    opt_type: str,
    entry: float,
    sl: float,
    target: float,
    qty: int | None = None,
    trail_sl: float | None = None,
) -> str:
    text = format_signal(index, expiry, opt_type, entry, sl, target)
    if qty is not None:
        text = f"{text} qty {qty}"
    if trail_sl is not None:
        text = f"{text} trail_sl {trail_sl:.0f}"
    return text

def calc_trailing_stop(
    current_price: float,
    entry_price: float,
    current_sl: float,
    trail_after_points: float,
    trail_step_points: float,
) -> float:
    profit_points = current_price - entry_price
    if profit_points < trail_after_points:
        return current_sl
    new_sl = current_price - trail_step_points
    return max(current_sl, new_sl)