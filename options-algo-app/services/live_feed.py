from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import streamlit as st

try:
    from dhanhq import marketfeed
except Exception as e:
    marketfeed = None
    _IMPORT_ERROR = e
else:
    _IMPORT_ERROR = None


@dataclass
class TickerState:
    symbol: Optional[str] = None
    ltp: Optional[float] = None
    ltt: Optional[str] = None
    prev_close: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    raw: Dict[str, Any] = field(default_factory=dict)


class DhanLiveFeed:
    def __init__(
        self,
        on_tick: Optional[Callable[[TickerState], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.client_id = st.secrets.get("DHAN_CLIENT_ID", "")
        self.access_token = st.secrets.get("DHAN_ACCESS_TOKEN", "")
        self.on_tick = on_tick
        self.on_error = on_error
        self.feed = None
        self.connected = False
        self.latest_tick: Optional[TickerState] = None
        self.ticks: List[TickerState] = []

        if not self.client_id or not self.access_token:
            raise ValueError("Missing DHAN_CLIENT_ID or DHAN_ACCESS_TOKEN in Streamlit secrets.")

        if marketfeed is None:
            raise ImportError("dhanhq marketfeed module is unavailable.") from _IMPORT_ERROR

    def _emit_error(self, message: str) -> None:
        if self.on_error:
            self.on_error(message)

    def process_incoming_ticker(self, data: Any) -> TickerState:
        """
        Normalize one incoming ticker update into a standard object.

        Supports:
        - dict payloads from wrappers
        - JSON strings
        - raw packets passed by SDK callbacks, if already decoded upstream
        """
        payload = data

        if isinstance(data, bytes):
            try:
                payload = json.loads(data.decode("utf-8"))
            except Exception:
                payload = {"raw_bytes": data.hex()}

        elif isinstance(data, str):
            try:
                payload = json.loads(data)
            except Exception:
                payload = {"raw_text": data}

        if not isinstance(payload, dict):
            payload = {"raw": payload}

        symbol = (
            payload.get("symbol")
            or payload.get("trading_symbol")
            or payload.get("instrument")
            or payload.get("securityId")
            or payload.get("security_id")
        )

        ltp = payload.get("ltp") or payload.get("last_price") or payload.get("price")
        ltt = payload.get("ltt") or payload.get("timestamp") or payload.get("time")
        prev_close = payload.get("prev_close") or payload.get("prevClose") or payload.get("previous_close")

        try:
            ltp_f = float(ltp) if ltp is not None else None
        except Exception:
            ltp_f = None

        try:
            prev_close_f = float(prev_close) if prev_close is not None else None
        except Exception:
            prev_close_f = None

        change = None
        change_pct = None
        if ltp_f is not None and prev_close_f not in [None, 0]:
            change = ltp_f - prev_close_f
            change_pct = (change / prev_close_f) * 100

        tick = TickerState(
            symbol=str(symbol) if symbol is not None else None,
            ltp=ltp_f,
            ltt=str(ltt) if ltt is not None else None,
            prev_close=prev_close_f,
            change=change,
            change_pct=change_pct,
            raw=payload,
        )

        self.latest_tick = tick
        self.ticks.append(tick)

        if self.on_tick:
            self.on_tick(tick)

        return tick

    def _sdk_on_message(self, message: Any) -> None:
        self.process_incoming_ticker(message)

    def _sdk_on_connect(self, instance: Any) -> None:
        self.connected = True

    def _sdk_on_close(self, instance: Any) -> None:
        self.connected = False

    def _sdk_on_error(self, instance: Any, error: Any) -> None:
        self.connected = False
        self._emit_error(str(error))

    def connect_and_subscribe(self, instruments: list, subscription_type: str = "Ticker") -> bool:
        """
        Start Dhan websocket feed and subscribe to instruments.

        instruments format is typically:
        [
            [marketfeed.NSE_FNO, "65378"],
            [marketfeed.NSE_EQ, "1333"],
        ]
        """
        if marketfeed is None:
            self._emit_error("Dhan marketfeed client not installed.")
            return False

        self.feed = marketfeed(
            self.client_id,
            self.access_token,
            instruments,
            subscription_type,
            self._sdk_on_connect,
            self._sdk_on_message,
            self._sdk_on_close,
        )

        def runner():
            try:
                asyncio.run(self.feed.connect())
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.feed.connect())
            except Exception as e:
                self._emit_error(str(e))

        threading.Thread(target=runner, daemon=True).start()
        return True

    def subscribe_symbols(self, symbols: list, subscription_type: str = "Ticker") -> None:
        """
        Subscribe additional symbols after connection is established.
        """
        if self.feed is None:
            self._emit_error("Feed not connected.")
            return

        try:
            if hasattr(self.feed, "subscribe_symbols"):
                self.feed.subscribe_symbols(symbols)
            elif hasattr(self.feed, "subscribe_instruments"):
                asyncio.run(self.feed.subscribe_instruments(symbols, subscription_type))
            else:
                self._emit_error("Current dhanhq version does not expose subscribe_symbols.")
        except Exception as e:
            self._emit_error(str(e))

    def unsubscribe_symbols(self, symbols: list, subscription_type: str = "Ticker") -> None:
        if self.feed is None:
            self._emit_error("Feed not connected.")
            return

        try:
            if hasattr(self.feed, "unsubscribe_symbols"):
                self.feed.unsubscribe_symbols(symbols)
            else:
                self._emit_error("Current dhanhq version does not expose unsubscribe_symbols.")
        except Exception as e:
            self._emit_error(str(e))

    def get_latest_tick(self) -> Optional[TickerState]:
        return self.latest_tick

    def get_tick_history(self) -> List[TickerState]:
        return self.ticks