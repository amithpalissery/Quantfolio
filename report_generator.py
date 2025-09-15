# report_generator.py
import yfinance as yf
import re
from portfolio_manager import buy_stock, sell_stock, get_historical_price
from llm import get_llm_response, resolve_tickers_with_llm
import json

def generate_stock_report(query, trade_mode=False):
    """
    Generate stock analysis or execute a trade based on user query.
    Handles multiple tickers, specific questions, and trades.
    """
    print(f"DEBUG: User query received: {query}")

    # ----------------------------
    # Trade Mode (Buy/Sell)
    # ----------------------------
    if trade_mode:
        tickers = resolve_tickers_with_llm(query)
        if not tickers:
            raise ValueError("❌ Could not detect a valid NSE ticker from your trade instruction.")
        
        ticker = tickers[0] # Assume one ticker for trades
        qty_match = re.search(r"(\d+)", query)
        
        if not qty_match:
            raise ValueError("⚠️ Please specify a valid quantity (e.g., '10').")
        
        qty = int(qty_match.group(1))

        if qty <= 0:
            raise ValueError("⚠️ Quantity to trade must be a positive number.")

        stock = yf.Ticker(ticker)
        price = stock.info.get("currentPrice") or stock.info.get("regularMarketPrice")

        if "buy" in query.lower():
            buy_stock(ticker, price, qty)
            return f"✅ Bought {qty} of {ticker} @ {price}", ticker
        elif "sell" in query.lower():
            sell_stock(ticker, price, qty)
            return f"✅ Sold {qty} of {ticker} @ {price}", ticker
        else:
            raise ValueError("⚠️ Please specify Buy or Sell action.")

    # ----------------------------
    # Analysis Mode
    # ----------------------------
    
    # 1. Check for specific, non-analysis questions first
    if "good to buy" in query.lower() or "profit" in query.lower() or "loss" in query.lower():
        tickers = resolve_tickers_with_llm(query)
        if not tickers:
            raise ValueError("❌ Could not detect a valid NSE ticker from your query.")
            
        ticker = tickers[0]
        
        # Use LLM to determine the historical time frame
        prompt_days_ago = f"From the query '{query}', how many days ago is the user asking about? Respond with only the number of days. If none, respond with 0."
        days_ago_str = get_llm_response(prompt_days_ago)
        try:
            days_ago = int(days_ago_str.strip())
            if days_ago > 0:
                historical_price = get_historical_price(ticker, days_ago)
                current_price = yf.Ticker(ticker).info.get("regularMarketPrice")
                
                if historical_price and current_price:
                    profit_per_share = current_price - historical_price
                    analysis_prompt = f"""
                    A user wants to know about profit/loss on {ticker}.
                    - Current Price: {current_price}
                    - Price {days_ago} days ago: {historical_price}
                    - Profit/Loss per share: {profit_per_share}
                    Based on this, answer the user's question: "{query}"
                    """
                    response = get_llm_response(analysis_prompt)
                    return response, ticker
                else:
                    return f"❌ Could not fetch historical data for {ticker}.", ticker
        except ValueError:
            pass # Continue to general analysis if no number is found
    
    # 2. General Analysis - Handles single, multi-stock, and sector queries
    tickers = resolve_tickers_with_llm(query)
    
    if not tickers:
        # Check if the query is a sector analysis
        sector_prompt = f"Is the user's query about a general sector (e.g., 'IT sector', 'banking stocks')? Answer 'yes' or 'no'."
        is_sector_query = get_llm_response(sector_prompt).strip().lower()
        
        if is_sector_query == 'yes':
            sector_name_prompt = f"What is the sector mentioned in '{query}'? Respond with only the sector name."
            sector_name = get_llm_response(sector_name_prompt)
            
            # This part would require a list of stocks by sector, which you would need to add.
            # For now, let's assume we can query for top stocks in that sector.
            top_stocks_prompt = f"List the top 5 largest NSE stock tickers in the {sector_name} sector. Respond with a JSON list like ['TCS.NS', ...]."
            top_tickers_json = get_llm_response(top_stocks_prompt)
            try:
                tickers = json.loads(top_tickers_json)
                if not isinstance(tickers, list):
                    tickers = []
            except json.JSONDecodeError:
                tickers = []
        else:
            raise ValueError("❌ Could not detect a valid NSE ticker or sector from your query.")

    stock_data = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            
            # Fetch events
            events = []
            try:
                dividends = stock.dividends.tail(2).to_dict()
                if dividends: events.append(f"Recent Dividends: {dividends}")
            except: pass
            
            try:
                splits = stock.splits.tail(1).to_dict()
                if splits: events.append(f"Recent Splits: {splits}")
            except: pass
                
            data = {
                "ticker": ticker,
                "fundamentals": {
                    "Name": info.get("longName", "N/A"),
                    "Sector": info.get("sector", "N/A"),
                    "PE Ratio": info.get("trailingPE", "N/A"),
                    "Market Cap": info.get("marketCap", "N/A"),
                    "Price": price,
                },
                "events": "\n".join(events) if events else "No major recent corporate events found."
            }
            stock_data[ticker] = data
        except Exception as e:
            print(f"DEBUG: Failed to fetch data for {ticker}: {e}")
            stock_data[ticker] = {"error": f"Failed to fetch data for {ticker}"}

    # Generate the prompt for the LLM
    analysis_prompt = f"""
    You are a professional financial analyst. Provide a concise analysis for the following stock(s) based on the user's query: "{query}".
    
    Data:
    {json.dumps(stock_data, indent=2)}
    
    Instructions:
    - If a single stock, provide a detailed analysis of its fundamentals and recent events.
    - If multiple stocks, provide a comparative analysis.
    - If a sector query, provide a high-level overview of the sector based on the stocks provided.
    - Do not include any disclaimers or extra text.
    """
    
    response = get_llm_response(analysis_prompt)
    return response, tickers