import streamlit as st
from services.dhan import get_balance

st.title("👤 Portfolio")

bal = get_balance()

st.metric("Wallet Balance", f"₹{bal}")

if bal < 500:
    st.error("Low Balance")