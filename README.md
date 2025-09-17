# Quantfolio India - AI Stock Assistant

Quantfolio is an AI-powered financial analysis and portfolio management app for Indian stocks. It combines real-time data, context retrieval, and LLM-based analysis to help users make informed investment decisions and manage their portfolios interactively.

## Features
- **AI Stock Analysis:** Ask questions about any Indian stock, sector, or compare companies. Get concise, point-wise analysis powered by a Retrieval-Augmented Generation (RAG) system and LLM.
- **Portfolio Management:** Buy and sell stocks, view live prices, average buy price, and unrealized P&L. Reset your portfolio anytime.
- **Data Scraping:** Automatically scrapes and updates financial data for requested stocks from Screener.in and other sources.
- **Chat History:** Stores all your queries and AI responses for easy reference.

## Architecture & Workflow

### 1. Streamlit UI (`app.py`)
- Provides two main tabs: **AI Stock Assistant** and **Portfolio Manager**.
- Handles user queries, trade instructions, and displays results.
- Ensures scraped data is available before starting.
- Manages chat history and portfolio state.

### 2. Stock Analysis & RAG System
- **`report_generator.py`:**
  - Resolves tickers using LLM.
  - Scrapes  data of resolved tickers as needed.
  - Retrieves context from the RAG system (`rag_system.py`).
  - Combines real-time data (via yfinance) and context for LLM analysis.
  - Executes trades and returns confirmation with live price.
- **`rag_system.py`:**
  - Loads, chunks, and indexes scraped financial data using FAISS and sentence-transformers.
  - Retrieves relevant context for queries, supporting multi-ticker and sector analysis.

### 3. Data Scraping & Storage
- **`data_scraper.py`:**
  - Scrapes financial ratios, performance, news, and events for stocks.
  - Stores data in `scraped_data/` as JSON files.
- **`database.py`, `portfolio_manager.py`:**
  - Manages SQLite database for trades and holdings.
  - Calculates live price and unrealized P&L using yfinance.

### 4. LLM Integration (`llm.py`)
- Uses AWS Bedrock via LangChain for natural language understanding and ticker resolution.
- Handles multi-ticker and sector queries.

### 5. Chat History (`chat_history.py`)
- Stores and retrieves user queries and AI responses in a SQLite table.
- Allows deletion of individual chat entries.

## How It Works
1. **User Query:** Enter a question or trade instruction in the Streamlit UI.
2. **Ticker Resolution:** LLM identifies relevant tickers (supports multi-ticker and sector queries).
3. **Data Scraping:** If data for a ticker is missing, it is scraped and stored automatically.
4. **Context Retrieval:** RAG system fetches relevant financial data and news for the query.
5. **LLM Analysis:** Combines context and real-time data for a concise, actionable report.
6. **Portfolio Actions:** Buy/sell trades update the database and show confirmation with live price.
7. **Portfolio View:** See all holdings, live prices, average buy price, and unrealized P&L.
8. **Chat History:** All interactions are saved for future reference.

## Setup & Usage
1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Run the app:**
   ```bash
   streamlit run app.py
   ```
3. **Configure AWS Bedrock:**
   - Set your AWS credentials and region in `config.py`.

## Deployment Notes
- For containerization/Kubernetes, use IAM Roles for Service Accounts (IRSA) or environment variables for AWS credentials.
- Do not hardcode secrets in code or images.

## Folder Structure
```
Quantfolio/
│
├── app.py                  # Main Streamlit UI
├── config.py               # Configuration settings
├── requirements.txt
│
├── core/                   # Core business logic
│   ├── report_generator.py
│   ├── rag_system.py
│   ├── llm.py
│
├── data/                   # Data scraping and processing
│   ├── data_scraper.py
│   ├── data_fetcher.py
│
├── db/                     # Database and portfolio management
│   ├── portfolio_manager.py
│   ├── database.py
│   ├── chat_history.py
│
├── scraped_data/           # Scraped JSON data
│
├── portfolio.db, chat_history.db  # SQLite databases
│
└── README.md
```

## Contributing
Pull requests and suggestions are welcome!

## License
MIT
