from services.dhan_client import DhanClient

def build_order_payload(index, strike, opt_type, qty, side="BUY"):
    return {
        "transactionType": side,
        "exchangeSegment": "NSE_FNO",
        "productType": "INTRADAY",
        "orderType": "MARKET",
        "validity": "DAY",
        "securityId": str(strike),
        "quantity": int(qty),
        "disclosedQuantity": 0,
        "price": 0,
        "triggerPrice": 0,
        "correlationId": f"{index}-{strike}-{opt_type}",
        "remarks": f"{index} {strike} {opt_type}",
    }

def place_market_order(index, strike, opt_type, qty):
    client = DhanClient()
    payload = build_order_payload(index, strike, opt_type, qty)
    return client.place_order(payload)