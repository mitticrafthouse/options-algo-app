from __future__ import annotations

def required_capital(entry_price: float, lot_size: int, lots: int) -> float:
    return float(entry_price) * int(lot_size) * int(lots)

def can_place_order(balance: float, required: float) -> bool:
    return float(balance) >= float(required)