from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

DHAN_BASE_URL = "https://api.dhan.co/v2"


@dataclass
class BrokerConnection:
    client_id: str
    access_token: str
    connected: bool = False
    balance: float = 0.0
    broker_name: str = "Dhan"


def _session(access_token: str) -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "Content-Type": "application/json",
            "access-token": access_token,
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        }
    )
    return s


def connect_broker(client_id: str, access_token: str) -> BrokerConnection:
    if not client_id or not access_token:
        raise ValueError("Client ID and Access Token are required.")
    bal = get_dhan_balance(access_token)
    return BrokerConnection(
        client_id=client_id.strip(),
        access_token=access_token.strip(),
        connected=True,
        balance=float(bal or 0.0),
    )


def get_dhan_balance(access_token: str) -> Optional[float]:
    try:
        s = _session(access_token)
        r = s.get(f"{DHAN_BASE_URL}/fundlimit", timeout=15)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            if "availabelBalance" in data:
                return float(data["availabelBalance"])
            if "availableBalance" in data:
                return float(data["availableBalance"])
        return None
    except Exception:
        return None


def place_market_order(access_token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        s = _session(access_token)
        r = s.post(f"{DHAN_BASE_URL}/orders", json=payload, timeout=15)
        r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return {"status": "OK", "message": "Order placed successfully."}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}


def modify_order(access_token: str, order_id: str, trigger_price: float, price: float = 0.0) -> Dict[str, Any]:
    try:
        s = _session(access_token)
        payload = {
            "orderId": order_id,
            "triggerPrice": trigger_price,
            "price": price,
        }
        r = s.put(f"{DHAN_BASE_URL}/orders/{order_id}", json=payload, timeout=15)
        r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return {"status": "OK", "message": "Order modified successfully."}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}


def required_capital_estimate(entry_price: float, lot_size: int, lots: int) -> float:
    return float(entry_price) * int(lot_size) * int(lots)


def validate_order_funds(access_token: str, required_margin: float) -> Dict[str, Any]:
    balance = get_dhan_balance(access_token)
    if balance is None:
        return {
            "ok": False,
            "status": "ERROR",
            "message": "Unable to fetch Dhan balance.",
            "available_balance": None,
            "required_margin": float(required_margin),
        }

    if balance < required_margin:
        return {
            "ok": False,
            "status": "INSUFFICIENT_FUNDS",
            "message": f"Insufficient balance. Available ₹{balance:,.0f}, required ₹{required_margin:,.0f}.",
            "available_balance": float(balance),
            "required_margin": float(required_margin),
        }

    return {
        "ok": True,
        "status": "OK",
        "message": "Sufficient balance.",
        "available_balance": float(balance),
        "required_margin": float(required_margin),
    }


def place_order_if_funds_ok(
    client_id: str,
    access_token: str,
    order_payload: Dict[str, Any],
    required_margin: float,
) -> Dict[str, Any]:
    funds = validate_order_funds(access_token, required_margin)
    if not funds["ok"]:
        return funds

    order_resp = place_market_order(access_token, order_payload)
    return {
        "ok": True,
        "status": "ORDER_SENT",
        "message": "Order sent to Dhan.",
        "available_balance": funds["available_balance"],
        "required_margin": funds["required_margin"],
        "order_response": order_resp,
        "client_id": client_id,
    }