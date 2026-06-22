import requests
import streamlit as st

class DhanClient:
    def __init__(self):
        self.client_id = st.secrets.get("DHAN_CLIENT_ID", "")
        self.access_token = st.secrets.get("DHAN_ACCESS_TOKEN", "")
        self.base_url = "https://api.dhan.co/v2"
        self.headers = {
            "Content-Type": "application/json",
            "access-token": self.access_token,
        }

    def _get(self, path, params=None):
        url = f"{self.base_url}{path}"
        return requests.get(url, headers=self.headers, params=params, timeout=20)

    def _post(self, path, payload):
        url = f"{self.base_url}{path}"
        return requests.post(url, headers=self.headers, json=payload, timeout=20)

    def historical_data(self, exchange_segment, instrument_id, interval, from_date, to_date):
        payload = {
            "exchangeSegment": exchange_segment,
            "instrumentId": instrument_id,
            "interval": interval,
            "fromDate": from_date,
            "toDate": to_date,
        }
        return self._post("/historical-data", payload)

    def place_order(self, payload):
        return self._post("/orders", payload)

    def order_book(self):
        return self._get("/orders")

    def trade_book(self):
        return self._get("/trades")