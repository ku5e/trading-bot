"""
Trading bot configuration.
Copy .env.example to .env and fill in your values before running.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Alpaca credentials — set in .env
ALPACA_API_KEY = os.environ["ALPACA_API_KEY"]
ALPACA_SECRET_KEY = os.environ["ALPACA_SECRET_KEY"]
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

# Ollama endpoint — set in .env or defaults to localhost
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

# Risk guardrails — enforced in code, never overridden by LLM
MAX_POSITION_SIZE_USD = 5000      # max dollars in any single position
MAX_ACCOUNT_RISK_PCT = 0.10      # max 10% of account in one trade
TRAILING_STOP_DROP_PCT = 0.10    # sell if drops 10% from entry
TRAILING_STOP_RAISE_TRIGGER = 0.10  # raise floor when up 10%
TRAILING_STOP_FLOOR_OFFSET = 0.05   # new floor = current price - 5%

# Politician copy settings
CAPITOL_TRADES_URL = "https://capitoltrades.com/trades"
COPY_TRADE_DELAY_DAYS = 0        # buy immediately on disclosure
COPY_MAX_POSITION_USD = 5000     # max per copy trade position

# Email
EMAIL_SMTP = os.getenv("EMAIL_SMTP", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASS = os.getenv("EMAIL_PASS", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")

# Scheduler
MARKET_OPEN = "09:30"
MARKET_CLOSE = "16:00"
TRAILING_CHECK_INTERVAL_MINUTES = 5
POLITICIAN_CHECK_INTERVAL_HOURS = 24
