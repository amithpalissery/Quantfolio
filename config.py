# config.py
DB_PATH = "db/portfolio.db"
DEFAULT_QUANTITY = 10
TRADE_COOLDOWN_DAYS = 7

# Bedrock settings
REGION_NAME = "us-east-1"
BEDROCK_MODEL = "anthropic.claude-3-sonnet-20240229-v1:0" 

# New: LangChain chat memory
MEMORY_KEY = "chat_history"