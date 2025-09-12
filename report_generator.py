# report_generator.py
import yfinance as yf
import re
from portfolio_manager import buy_stock, sell_stock
from llm import get_llm_response, resolve_ticker_with_llm

def generate_stock_report(query, trade_mode=False):
    """
    Generate stock analysis or execute a trade based on user query.
    Uses LLM to detect ticker and yfinance for live market data.
    Includes corporate events.
    """
    print(f"DEBUG: User query received: {query}")

    # ----------------------------
    # Resolve ticker using LLM
    # ----------------------------
    ticker = resolve_ticker_with_llm(query)
    if not ticker:
        raise ValueError("❌ Could not detect a valid NSE ticker from your query.")

    # ----------------------------
    # Fetch stock info from yfinance
    # ----------------------------
    stock = yf.Ticker(ticker)
    info = stock.info
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    print(f"DEBUG: Current stock price: {price}")

    if not price:
        raise ValueError(f"❌ Could not fetch live price for {ticker}")

    # ----------------------------
    # Trade Mode (Buy/Sell)
    # ----------------------------
    if trade_mode:
        qty_match = re.search(r"(\d+)", query)
        qty = int(qty_match.group(1)) if qty_match else 1

        if "buy" in query.lower():
            buy_stock(ticker, price, qty)
            return f"✅ Bought {qty} of {ticker} @ {price}", ticker
        elif "sell" in query.lower():
            sell_stock(ticker, price, qty)
            return f"✅ Sold {qty} of {ticker} @ {price}", ticker
        else:
            raise ValueError("⚠️ Please specify Buy or Sell action.")

    # ----------------------------
    # Corporate Events
    # ----------------------------
    events = []

    try:
        dividends = stock.dividends.tail(5)
        if not dividends.empty:
            events.append(f"Recent Dividends: {dividends.to_dict()}")
    except Exception as e:
        print(f"DEBUG: Error fetching dividends: {e}")

    try:
        splits = stock.splits.tail(3)
        if not splits.empty:
            events.append(f"Recent Splits: {splits.to_dict()}")
    except Exception as e:
        print(f"DEBUG: Error fetching splits: {e}")

    try:
        actions = stock.actions.tail(5)
        if not actions.empty:
            events.append(f"Recent Corporate Actions: {actions.to_dict()}")
    except Exception as e:
        print(f"DEBUG: Error fetching actions: {e}")

    try:
        earnings = stock.earnings_dates.head(5)
        if earnings is not None and not earnings.empty:
            events.append("Upcoming Earnings:\n" + earnings.to_string())
    except Exception as e:
        print(f"DEBUG: Error fetching earnings dates: {e}")

    events_summary = "\n".join(events) if events else "No major recent corporate events found."

    # ----------------------------
    # AI Analysis Prompt
    # ----------------------------
    fundamentals = {
        "Name": info.get("longName", "N/A"),
        "Sector": info.get("sector", "N/A"),
        "Industry": info.get("industry", "N/A"),
        "Market Cap": info.get("marketCap", "N/A"),
        "PE Ratio": info.get("trailingPE", "N/A"),
        "Price": price,
    }

    prompt = f"""
You are a professional financial analyst. Provide a concise analysis of {fundamentals['Name']} ({ticker}).

Instructions:
- First, list 3 bullet points about fundamentals (Market Cap, Sector, PE, Price, etc.).
- Then, list 2-3 bullet points about recent corporate events (dividends, splits, earnings) if any.
- If no corporate events, say "No major recent corporate events".
- Do not include any disclaimers or extra text.

Fundamentals:
{fundamentals}

Corporate Events:
{events_summary}
"""

    print(f"DEBUG: Sending prompt to LLM:\n{prompt}")

    response = get_llm_response(prompt)
    print(f"DEBUG: LLM response:\n{response}")

    return response.strip(), ticker
