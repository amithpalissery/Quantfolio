import yfinance as yf
import pandas as pd

def get_fundamentals(ticker: str):
    stock = yf.Ticker(ticker)
    info = stock.info

    return {
        "PE": info.get("trailingPE"),
        "PB": info.get("priceToBook"),
        "ROE": info.get("returnOnEquity"),
        "Debt_Equity": info.get("debtToEquity"),
        "EPS": info.get("trailingEps"),
        "MarketCap": info.get("marketCap"),
    }

def get_technicals(ticker: str):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="6mo")

    # Moving averages
    hist["50DMA"] = hist["Close"].rolling(50).mean()
    hist["200DMA"] = hist["Close"].rolling(200).mean()

    # Simple RSI
    delta = hist["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    hist["RSI"] = 100 - (100 / (1 + rs))

    latest = hist.iloc[-1]

    return {
        "RSI": round(latest["RSI"], 2),
        "50DMA": round(latest["50DMA"], 2),
        "200DMA": round(latest["200DMA"], 2),
        "LastPrice": round(latest["Close"], 2)
    }
