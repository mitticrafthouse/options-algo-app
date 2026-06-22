from dataclasses import dataclass

@dataclass
class Signal:
    signal: str
    side: str
    action: str
    reason: str
    entry_price: float | None = None
    target_price: float | None = None
    stop_loss_price: float | None = None
    trailing_stop_price: float | None = None
    confidence: int = 0
    timestamp: str | None = None
    strategy_name: str = ""