from dataclasses import dataclass

LOT_SIZES = {
    "NIFTY": 65,
    "BANKNIFTY": 30,
    "FINNIFTY": 60,
    "SENSEX": 20,
}

INSTRUMENTS = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX"]
OPTION_TYPES = ["CE", "PE"]
MODES = ["AUTO", "MANUAL", "BACKTEST"]


@dataclass
class StrategyConfig:
    name: str
    instrument: str
    timeframe: str = "5m"
    ema_fast: int = 9
    ema_slow: int = 21
    target_points: float = 45.0
    sl_points: float = 12.0
    trail_after_points: float = 15.0
    trail_step_points: float = 8.0
    use_trailing_stop: bool = True
    use_volume_filter: bool = True
    active: bool = True