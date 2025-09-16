# utils.py
import streamlit as st

# This function needs access to the cached function in app.py
def clear_report_cache():
    st.cache_data.clear()