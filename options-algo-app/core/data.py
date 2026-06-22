from __future__ import annotations

import pandas as pd
import requests

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json,text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
}

def nse_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(NSE_HEADERS)
    s.get("https://www.nseindia.com", timeout=10)
    return s

def fetch_option_chain(index: str) -> dict:
    index = index.upper().strip()
    s = nse_session()
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={index}"
    r = s.get(url, timeout=10)
    r.raise_for_status()
    return r.json()

def fetch_live_ltp(index: str) -> float | None:
    try:
        data = fetch_option_chain(index)
        records = data.get("records", {}).get("data", [])
        for row in records:
            ce = row.get("CE")
            pe = row.get("PE")
            if ce and "lastPrice" in ce:
                return float(ce["lastPrice"])
            if pe and "lastPrice" in pe:
                return float(pe["lastPrice"])
    except Exception:
        return None
    return None

def fetch_candles_mock(index: str) -> pd.DataFrame:
    data = [
        ["2026-06-22 09:15", 23500, 23520, 23490, 23510, 120000],
        ["2026-06-22 09:20", 23510, 23540, 23500, 23530, 135000],
        ["2026-06-22 09:25", 23530, 23545, 23505, 23515, 140000],
        ["2026-06-22 09:30", 23515, 23535, 23495, 23525, 150000],
        ["2026-06-22 09:35", 23525, 23560, 23520, 23550, 160000],
        ["2026-06-22 09:40", 23550, 23572, 23535, 23568, 175000],
        ["2026-06-22 09:45", 23568, 23605, 23560, 23598, 182000],
        ["2026-06-22 09:50", 23598, 23620, 23570, 23612, 190000],
        ["2026-06-22 09:55", 23612, 23618, 23585, 23592, 165000],
        ["2026-06-22 10:00", 23592, 23605, 23570, 23578, 158000],
    ]
    return pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])