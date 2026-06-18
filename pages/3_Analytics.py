import streamlit as st
import pandas as pd

st.title("📊 Trade Analytics")

if "history" in st.session_state:

    df = pd.DataFrame(st.session_state.history)

    if not df.empty:
        st.dataframe(df)

        st.line_chart(df["pnl"])
    else:
        st.info("No trades yet")