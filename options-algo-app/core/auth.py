import streamlit as st

def is_authenticated():
    return st.session_state.get("authenticated", False)

def authenticate(password: str) -> bool:
    app_password = st.secrets.get("APP_PASSWORD", "")
    if password and password == app_password:
        st.session_state["authenticated"] = True
        return True
    return False

def logout():
    st.session_state["authenticated"] = False
    st.rerun()