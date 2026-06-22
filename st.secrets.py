import os
import streamlit as st

def get_secret(key, default=""):
    try:
        return st.secrets.get(key, os.environ.get(key, default))
    except Exception:
        return os.environ.get(key, default)

APP_PASSWORD = get_secret("APP_PASSWORD")
DHAN_CLIENT_ID = get_secret("DHAN_CLIENT_ID")
DHAN_ACCESS_TOKEN = get_secret("DHAN_ACCESS_TOKEN")