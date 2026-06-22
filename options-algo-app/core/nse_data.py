from __future__ import annotations

import requests

FALLBACK_LOT_SIZES = {
    "NIFTY": 65,
    "BANKNIFTY": 30,
    "FINNIFTY": 60,
    "SENSEX": 20,
}

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json,text/html,application/xhtml+xml",
    "Referer": "https://www.nseindia.com/",
}

def get_live_lot_size(index: str) -> int:
    index = index.upper().strip()
    fallback = FALLBACK_LOT_SIZES.get(index, 1)
    try:
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=HEADERS, timeout=10)
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={index}"
        r = s.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        records = data.get("records", {}).get("data", [])
        for row in records:
            for side in ("CE", "PE"):
                if side in row and "marketLot" in row[side]:
                    return int(row[side]["marketLot"])
        return fallback
    except Exception:
        return fallback