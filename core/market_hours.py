from datetime import datetime, time
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

def market_is_open(now: datetime | None = None) -> bool:
    now = now or datetime.now(IST)
    if now.weekday() > 4:
        return False
    t = now.time()
    return time(9, 15) <= t <= time(15, 30)