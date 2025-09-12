# chat_history.py
import sqlite3
from config import DB_PATH

def init_chat_history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT,
        response TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

def save_chat(query, response):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO chat_history (query, response) VALUES (?, ?)", (query, response))
    conn.commit()
    conn.close()

def get_chat_history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # make sure table exists
    c.execute("""
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT,
        response TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()

    c.execute("SELECT id, query, response FROM chat_history ORDER BY id ASC")
    history = [{"id": row[0], "query": row[1], "response": row[2]} for row in c.fetchall()]
    conn.close()
    return history

def delete_chat(chat_id):
    """Delete a chat entry by its id"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM chat_history WHERE id=?", (chat_id,))
    conn.commit()
    conn.close()
