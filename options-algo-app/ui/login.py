import streamlit as st
from core.auth import authenticate

def render_login():
    st.title("Login")
    st.caption("Protected access to the trading dashboard")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        if authenticate(password):
            st.session_state["username"] = username or "trader"
            st.rerun()
        st.error("Invalid password")