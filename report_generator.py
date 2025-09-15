# report_generator.py (Updated)
import yfinance as yf
from llm import get_llm_response, resolve_tickers_with_llm
from rag_system import RAGSystem # NEW: Import RAG System
from portfolio_manager import get_live_price, buy_stock, sell_stock, get_historical_price

# Initialize the RAG system globally
rag_system = RAGSystem()

def generate_stock_report(query, trade_mode=False):
    """
    Generates a financial report based on the query.
    Uses the RAG system to retrieve context from the scraped data.
    """
    # 1. Resolve Tickers
    detected_tickers = resolve_tickers_with_llm(query)
    if not detected_tickers:
        return "I could not identify any valid stock tickers in your query. Please specify a valid NSE stock.", []

    # 2. Get the primary ticker (for simplicity)
    main_ticker = detected_tickers[0]

    if trade_mode:
        # Trade mode logic remains the same, as it's action-oriented, not report-based
        action, quantity = get_trade_action(query)
        price = get_live_price(main_ticker)
        if not price:
            return f"Could not get live price for {main_ticker}.", []
        
        if action == "buy":
            buy_stock(main_ticker, price, quantity)
            return f"✅ BUY order executed: {quantity} shares of {main_ticker} at {price:.2f}", []
        elif action == "sell":
            try:
                sell_stock(main_ticker, price, quantity)
                return f"✅ SELL order executed: {quantity} shares of {main_ticker} at {price:.2f}", []
            except RuntimeError as e:
                return f"⚠️ {e}", []
        else:
            return "I could not understand the trade command.", []

    else:
        # 3. Retrieve context from the RAG system
        retrieved_context = rag_system.get_context(query, k=3)
        if not retrieved_context:
            print("No relevant context found in the RAG system.")
            retrieved_context = "No specific data available from screener.in for this query."
        
        # 4. Fetch additional real-time data from yfinance
        try:
            live_price = get_live_price(main_ticker)
            if live_price:
                yfinance_context = f"Live Price of {main_ticker}: {live_price:.2f}"
            else:
                yfinance_context = f"Could not fetch live price for {main_ticker} from yfinance."
        except Exception:
            yfinance_context = "Could not fetch live data."
        
        # 5. Combine all context into a single, comprehensive prompt for the LLM
        prompt = f"""
You are an expert financial analyst. Your task is to provide a concise, point-wise analysis of the stock based on the user's query and the provided context.

Follow this exact numbered and bullet-point format:

1.  **Summary of Key Findings**
    - **Valuation**: [One sentence on valuation and overall health]
    - **Perfomance**: [One sentence on recent performance]
    - **Future outlook**: [One sentence on the future outlook or key risk/opportunity]

2.  **Key Financial Metrics**
    - **Live Price**: [from yfinance context]
    - [Include key metrics like P/E, Market Cap, etc. from the scraped data in the RAG context]
    - [Other relevant metrics]

3.  **Recent News/Events**
    - [Extract key events from the context, if available]
    - [Summarize any management commentary]

4. **Deatils**
    - [summarize and give as points the reamining info retrieved]

---
**Context from Screener.in:**
{retrieved_context}
---
**Real-time Data:**
{yfinance_context}
---
**User Query:**
{query}
"""
        # 6. Get the LLM's response
        llm_response = get_llm_response(prompt)
        return llm_response, detected_tickers

def get_trade_action(query):
    # This function needs to be a bit more robust for production,
    # but for now, we'll keep the basic buy/sell logic
    query_lower = query.lower()
    quantity = 1
    if "buy" in query_lower:
        parts = query_lower.split("buy")
        if len(parts) > 1 and parts[0].strip().isdigit():
            quantity = int(parts[0].strip())
        return "buy", quantity
    elif "sell" in query_lower:
        parts = query_lower.split("sell")
        if len(parts) > 1 and parts[0].strip().isdigit():
            quantity = int(parts[0].strip())
        return "sell", quantity
    return None, None