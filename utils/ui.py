import streamlit as st

def pnl_bar(pnl):

    color = "green" if pnl >= 0 else "red"

    st.markdown(f"""
    <div style="
        width:100%;
        padding:10px;
        background:{color};
        color:black;
        border-radius:8px;
        text-align:center;
        font-weight:bold;
    ">
        PnL: ₹{round(pnl,2)}
    </div>
    """, unsafe_allow_html=True)
