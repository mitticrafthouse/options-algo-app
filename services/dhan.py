import streamlit as st

def get_balance():
    try:
        from dhanhq import dhanhq
        client = dhanhq(
            st.secrets["CLIENT_ID"],
            st.secrets["ACCESS_TOKEN"]
        )
        data = client.get_fund_limits()
        return data["data"].get("availabelBalance", 0)
    except:
        return 0


def place_order(symbol, qty):
    try:
        from dhanhq import dhanhq
        client = dhanhq(
            st.secrets["CLIENT_ID"],
            st.secrets["ACCESS_TOKEN"]
        )

        client.place_order(
            trading_symbol=symbol,
            exchange_segment="NSE_FNO",
            transaction_type="BUY",
            quantity=qty,
            order_type="MARKET",
            product_type="INTRADAY"
        )

        return "FILLED ✅"

    except Exception as e:
        return f"FAILED ❌ {e}"