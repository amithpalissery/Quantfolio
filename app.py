import streamlit as st
import pandas as pd
from database import init_db
from report_generator import generate_stock_report
from portfolio_manager import portfolio_status, reset_portfolio
from chat_history import get_chat_history, save_chat, init_chat_history, delete_chat
from llm import memory  # Import the shared memory object
from config import MEMORY_KEY
import os
import subprocess

# -----------------------------
# Init DBs and Session State
# -----------------------------
init_db()
init_chat_history()

st.set_page_config(page_title="Quantfolio India", layout="wide")

st.title("📈 Quantfolio India - AI Stock Assistant")

# Check if scraped_data folder exists and is not empty
SCRAPED_DATA_PATH = "scraped_data"
def ensure_scraped_data():
    if not os.path.exists(SCRAPED_DATA_PATH) or not os.listdir(SCRAPED_DATA_PATH):
        st.warning("Scraped data not found or empty. Running data scraper...")
        subprocess.run(["python3", "data_scraper.py"])  # Run the scraper
        st.success("Data scraping completed. Please rerun the app if needed.")
        st.stop()

ensure_scraped_data()

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
                # Clear memory and rerun to avoid state issues
                memory.clear()
                st.rerun()
else:
    st.sidebar.write("No past queries yet.")

# -----------------------------
# Tabs
# -----------------------------
tab1, tab2 = st.tabs(["💬 AI Stock Assistant", "📊 Portfolio Manager"])

def get_report_and_tickers(query, trade_mode=False):
    return generate_stock_report(query, trade_mode=trade_mode)

def get_portfolio_status():
    return portfolio_status()

# -----------------------------
# Tab 1: AI Assistant
# -----------------------------
with tab1:
    st.subheader("Ask about any Indian stock, sector, or compare companies")
    query = st.text_input("Your Query:", key="ai_query_input")
    
    if st.button("Get Analysis", width='stretch'):
        if query:
            try:
                with st.spinner("Fetching data & generating report..."):
                    report, detected_tickers = get_report_and_tickers(query)

                st.markdown("### 📌 AI Analysis")
                st.write(report)

                if detected_tickers:
                    st.success(f"Detected Tickers: {', '.join(detected_tickers)}")
                    
                # Store the query and response
                save_chat(query, report)
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
    data = get_portfolio_status()
    if data:
        df = pd.DataFrame(data, columns=["Stock", "Quantity", "Avg Buy Price", "Live Price", "Unrealized P&L"])
        st.dataframe(df, width='stretch')
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
    trade_query = st.text_input("Enter trade instruction (e.g. 'Buy 10 Reliance', 'Sell 5 ICICI Bank')", key="trade_input")
    
    if st.button("Execute Trade", key="execute_trade_button"):
        if trade_query:
            try:
                with st.spinner("Processing trade..."):
                    result, _ = get_report_and_tickers(trade_query, trade_mode=True)
                st.success(result)
                save_chat(trade_query, result)
                # Clear the cache for portfolio status so it updates immediately
                st.rerun()
            except Exception as e:
                st.error(f"Error executing trade: {e}")
        else:
            st.warning("Please enter a trade instruction.")