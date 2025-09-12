# portfolio_manager.py
import sqlite3
import yfinance as yf
from config import DB_PATH, DEFAULT_QUANTITY

def buy_stock(ticker, price, qty=DEFAULT_QUANTITY):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Create holdings table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS holdings (
            stock TEXT PRIMARY KEY,
            quantity INTEGER,
            avg_price REAL
        )
    """)

    # Update or insert holding
    cur.execute("SELECT quantity, avg_price FROM holdings WHERE stock=?", (ticker,))
    row = cur.fetchone()
    if row:
        old_qty, old_avg = row
        new_qty = old_qty + qty
        new_avg = (old_qty * old_avg + qty * price) / new_qty
        cur.execute("UPDATE holdings SET quantity=?, avg_price=? WHERE stock=?", (new_qty, new_avg, ticker))
    else:
        cur.execute("INSERT INTO holdings (stock, quantity, avg_price) VALUES (?, ?, ?)", (ticker, qty, price))

    # Create trades table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock TEXT,
            action TEXT,
            price REAL,
            quantity INTEGER,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Log trade
    cur.execute("INSERT INTO trades (stock, action, price, quantity) VALUES (?, ?, ?, ?)",
                (ticker, "BUY", price, qty))

    conn.commit()
    conn.close()


def sell_stock(ticker, price, qty=DEFAULT_QUANTITY):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS holdings (
            stock TEXT PRIMARY KEY,
            quantity INTEGER,
            avg_price REAL
        )
    """)

    cur.execute("SELECT quantity, avg_price FROM holdings WHERE stock=?", (ticker,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise RuntimeError(f"⚠️ No holdings found for {ticker}")

    old_qty, old_avg = row
    if qty > old_qty:
        qty = old_qty

    new_qty = old_qty - qty
    if new_qty <= 0:
        cur.execute("DELETE FROM holdings WHERE stock=?", (ticker,))
    else:
        cur.execute("UPDATE holdings SET quantity=?, avg_price=? WHERE stock=?", (new_qty, old_avg, ticker))

    # Create trades table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock TEXT,
            action TEXT,
            price REAL,
            quantity INTEGER,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Log trade
    cur.execute("INSERT INTO trades (stock, action, price, quantity) VALUES (?, ?, ?, ?)",
                (ticker, "SELL", price, qty))

    conn.commit()
    conn.close()


def portfolio_status():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS holdings (
            stock TEXT PRIMARY KEY,
            quantity INTEGER,
            avg_price REAL
        )
    """)

    cur.execute("SELECT stock, quantity, avg_price FROM holdings")
    holdings = cur.fetchall()

    status = []
    for stock, qty, avg in holdings:
        try:
            live_price = yf.Ticker(stock).info.get("regularMarketPrice", None)
        except Exception:
            live_price = None
        unrealized = (live_price - avg) * qty if live_price else None
        status.append((stock, qty, avg, live_price, unrealized))

    conn.close()
    return status


def get_live_price(ticker):
    try:
        return yf.Ticker(ticker).info.get("regularMarketPrice", None)
    except Exception:
        return None


def reset_portfolio():
    """Delete all holdings and trades."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS holdings")
    cur.execute("DROP TABLE IF EXISTS trades")
    conn.commit()
    conn.close()
