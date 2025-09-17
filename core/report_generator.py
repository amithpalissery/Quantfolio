# report_generator.py
import yfinance as yf
from core.llm import get_llm_response, resolve_tickers_with_llm
from core.rag_system import RAGSystem
from db.portfolio_manager import get_live_price, buy_stock, sell_stock, get_historical_price
from data.data_scraper import scrape_and_save_data
import streamlit as st
from datetime import date

# Initialize the RAG system globally
rag_system = RAGSystem()
today = date.today()

def generate_stock_report(query, trade_mode=False):
    """
    Generates a financial report based on the query.
    Uses the RAG system to retrieve context from the scraped data.
    """
    # 1. Resolve Tickers
    detected_tickers = resolve_tickers_with_llm(query)
    if not detected_tickers:
        return "I could not identify any valid stock tickers in your query. Please specify a valid NSE stock.", []

    full_ticker = detected_tickers[0]
    clean_ticker = full_ticker.removesuffix('.NS')

    if trade_mode:
        # Only update DB, do not scrape data
        action, quantity = get_trade_action(query)
        # Always resolve ticker to .NS format
        full_ticker = detected_tickers[0]
        clean_ticker = full_ticker.removesuffix('.NS')
        price = get_live_price(full_ticker)
        price_str = f"{price:.2f}" if price is not None else "N/A"
        if action == "buy":
            buy_stock(full_ticker, price if price is not None else 0, quantity)
            return f"✅ BUY order executed: {quantity} shares of {full_ticker} at {price_str}", []
        elif action == "sell":
            try:
                sell_stock(full_ticker, price if price is not None else 0, quantity)
                return f"✅ SELL order executed: {quantity} shares of {full_ticker} at {price_str}", []
            except RuntimeError as e:
                return f"⚠️ {e}", []
        else:
            return "I could not understand the trade command.", []
    else:
        # Scrape data for all tickers that are not available
        missing_clean_tickers = []
        for full_ticker in detected_tickers:
            clean_ticker = full_ticker.removesuffix('.NS')
            if clean_ticker not in rag_system.get_available_tickers():
                missing_clean_tickers.append(clean_ticker)
        if missing_clean_tickers:
            with st.spinner(f"Scraping new data for: {', '.join(missing_clean_tickers)}..."):
                scrape_and_save_data(missing_clean_tickers)
            st.rerun()
        # Retrieve context for all tickers
        all_context = ""
        all_yfinance = ""
        for full_ticker in detected_tickers:
            clean_ticker = full_ticker.removesuffix('.NS')
            context = rag_system.get_context(query, k=3, filter_ticker=clean_ticker)
            if not context:
                context = f"No specific data available from screener.in for {clean_ticker}."
            try:
                live_price = get_live_price(full_ticker)
                if live_price:
                    yfinance_context = f"Live Price of {full_ticker}: {live_price:.2f}"
                else:
                    yfinance_context = f"Could not fetch live price for {full_ticker} from yfinance."
            except Exception:
                yfinance_context = "Could not fetch live data."
            all_context += f"\n--- {clean_ticker} ---\n{context}\n"
            all_yfinance += f"\n--- {clean_ticker} ---\n{yfinance_context}\n"
        # Combine context and get LLM response
        prompt = f"""
You are an expert financial analyst. Your task is to provide a concise, point-wise analysis of stocks based on the user's query and the provided context
Also note that today's date is {today}.

Output Format Rules
If the user asks for a general stock query of one or more stocks:
1.  **Summary of Key Findings**
    - **Valuation**: [One sentence on valuation and overall health]
    - **Perfomance**: [One sentence on recent performance]
    - **Future outlook**: [One sentence on the future outlook or key risk/opportunity]

2.  **Key Financial Metrics**
    - **Live Price**: [from yfinance context]
    - [Include key metrics like P/E, Market Cap, etc. from the scraped data in the RAG context]
    - [Other relevant metrics]

3. **Deatils**
    - [summarize and give as points the reamining info retrieved]

If the user asks for specific details about one or more stock or a sector (e.g., shareholding, peer comparison, balance sheet, P&L, cash flow):
Respond only with the requested data of the identified stocks.

Present the data in a clear, well-formatted tabular format, use multiple tables if more than one stock is present.

After each table, provide 2-3 key bullet points with insights derived from the data presented in the table.

Constraints
Base all information strictly on the provided context.

Do not hallucinate or add any information that is not in the context.

Do not mention the user's request, for example, "Here is the analysis you asked for..."

Be brief and direct, adhering to the specified format.
---
**Context from Screener.in:**
{all_context}
---
**Real-time Data:**
{all_yfinance}
---
**User Query:**
{query}
"""
        llm_response = get_llm_response(prompt)
        return llm_response, detected_tickers

def get_trade_action(query):
    import re
    query_lower = query.lower()
    # Match 'buy 5 reliance' or 'sell 3 tcs'
    buy_match = re.search(r"buy\s+(\d+)", query_lower)
    sell_match = re.search(r"sell\s+(\d+)", query_lower)
    if buy_match:
        quantity = int(buy_match.group(1))
        return "buy", quantity
    elif sell_match:
        quantity = int(sell_match.group(1))
        return "sell", quantity
    return None, None