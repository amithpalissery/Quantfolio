import sqlite3
from config import DB_PATH

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Trades table
    c.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stock TEXT,
        action TEXT,
        quantity INTEGER,
        price REAL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Holdings table
    c.execute("""
    CREATE TABLE IF NOT EXISTS holdings (
        stock TEXT PRIMARY KEY,
        quantity INTEGER,
        avg_price REAL
    )
    """)

    conn.commit()
    conn.close()
