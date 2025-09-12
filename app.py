# app.py
import streamlit as st
import pandas as pd
from database import init_db
from report_generator import generate_stock_report
from portfolio_manager import buy_stock, sell_stock, portfolio_status, reset_portfolio
from chat_history import get_chat_history, save_chat, init_chat_history, delete_chat

# -----------------------------
# Init DBs
# -----------------------------
init_db()
init_chat_history()

st.set_page_config(page_title="Quantfolio India", layout="wide")

st.title("📈 Quantfolio India - AI Stock Assistant")

# Sidebar – show past queries with delete option
st.sidebar.header("Past Queries")
history = get_chat_history()
if history:
    for h in history:
        col1, col2 = st.sidebar.columns([4, 1])
        with col1:
            st.write("- " + h["query"])
        with col2:
            if st.button("❌", key=f"del_{h['id']}"):
                delete_chat(h["id"])
                st.rerun()
else:
    st.sidebar.write("No past queries yet.")

# -----------------------------
# Tabs
# -----------------------------
tab1, tab2 = st.tabs(["💬 AI Stock Assistant", "📊 Portfolio Manager"])

# -----------------------------
# Tab 1: AI Assistant
# -----------------------------
with tab1:
    st.subheader("Ask about any Indian stock or sector")
    query = st.text_input("Your Query:")

    if st.button("Get Analysis", use_container_width=True):
        if query:
            try:
                with st.spinner("Fetching data & generating report..."):
                    report, detected_ticker = generate_stock_report(query)

                st.markdown("### 📌 AI Analysis")
                st.write(report)

                if detected_ticker:
                    st.success(f"Detected Ticker: {detected_ticker}")

                # Save only query (not response)
                save_chat(query, "")
            except Exception as e:
                st.error(f"Error while generating report: {e}")
        else:
            st.warning("Please enter a query.")

# -----------------------------
# Tab 2: Portfolio Manager
# -----------------------------
with tab2:
    st.subheader("Manage Your Portfolio")

    # Show portfolio
    data = portfolio_status()
    if data:
        df = pd.DataFrame(data, columns=["Stock", "Quantity", "Avg Buy Price", "Live Price", "Unrealized P&L"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No holdings yet. Start trading!")

    # Reset Portfolio Button
    if st.button("🗑️ Reset Portfolio", type="primary"):
        try:
            reset_portfolio()
            st.success("✅ Portfolio reset successfully.")
            st.rerun()
        except Exception as e:
            st.error(f"Error resetting portfolio: {e}")

    st.markdown("---")

    # Trade Box
    st.markdown("### Place Trade")
    trade_query = st.text_input("Enter trade instruction (e.g. 'Buy 10 Reliance', 'Sell 5 ICICI Bank')")

    if st.button("Execute Trade"):
        if trade_query:
            try:
                with st.spinner("Processing trade..."):
                    result, _ = generate_stock_report(trade_query, trade_mode=True)
                st.success(result)
                save_chat(trade_query, "")
                st.rerun()
            except Exception as e:
                st.error(f"Error executing trade: {e}")
        else:
            st.warning("Please enter a trade instruction.")
