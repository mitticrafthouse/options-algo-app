import streamlit as st
from ui.dashboard import render_dashboard

st.set_page_config(page_title="Options Scalper Pro", layout="wide")
render_dashboard()