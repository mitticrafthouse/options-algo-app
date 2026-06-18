import sys
import os
# ✅ FIX: Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import streamlit as st
import random
import time

st.title("📡 Live Market Feed")

price = 23000

for _ in range(100):
    price += random.randint(-5, 5)
    st.write(f"Price: ₹{price}")
    time.sleep(0.5)
