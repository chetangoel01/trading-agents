"""Global configuration for the trading agent system."""

from __future__ import annotations

import os
from enum import Enum

from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Runtime environment
# ---------------------------------------------------------------------------
CANONICAL_TZ = os.getenv("CANONICAL_TZ", "America/New_York")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
RUN_MODE = os.getenv("RUN_MODE", "single")  # single | continuous | backtest


# ---------------------------------------------------------------------------
# API credentials
# ---------------------------------------------------------------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT")

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


# ---------------------------------------------------------------------------
# Models and routing
# ---------------------------------------------------------------------------
class ModelRole(str, Enum):
    EXTRACTION = "extraction"
    SYNTHESIS = "synthesis"
    DECISION = "decision"
    SENTIMENT = "sentiment"
    FEEDBACK = "feedback"


MODEL_MAP = {
    ModelRole.EXTRACTION: "qwen/qwen3-coder",
    ModelRole.SYNTHESIS: "anthropic/claude-sonnet-4-5",
    ModelRole.DECISION: "anthropic/claude-sonnet-4-5",
    ModelRole.SENTIMENT: "qwen/qwen3-coder",
    ModelRole.FEEDBACK: "anthropic/claude-sonnet-4-5",
}

MODEL_FALLBACKS = {
    ModelRole.EXTRACTION: ["anthropic/claude-sonnet-4-5"],
    ModelRole.SYNTHESIS: ["qwen/qwen3-coder"],
    ModelRole.DECISION: ["qwen/qwen3-coder"],
    ModelRole.SENTIMENT: ["anthropic/claude-sonnet-4-5"],
    ModelRole.FEEDBACK: ["qwen/qwen3-coder"],
}

MODEL_MAX_TOKENS = {
    "qwen/qwen3-coder": 8192,
    "anthropic/claude-sonnet-4-5": 8192,
}

MODEL_TEMPERATURE = {
    ModelRole.EXTRACTION: 0.0,
    ModelRole.SYNTHESIS: 0.2,
    ModelRole.DECISION: 0.1,
    ModelRole.SENTIMENT: 0.0,
    ModelRole.FEEDBACK: 0.2,
}


# ---------------------------------------------------------------------------
# Trading universe and scheduling
# ---------------------------------------------------------------------------
WATCHLIST = os.getenv("WATCHLIST", "AAPL,MSFT,GOOGL,AMZN,NVDA").split(",")

STARTING_PAPER_CAPITAL_USD = 100000.0

# ET schedule windows, interpreted in CANONICAL_TZ.
SCHEDULE_PREMARKET_ANALYSIS = "09:00"  # no execution
SCHEDULE_INTERVAL_MINUTES = 30
SCHEDULE_EXECUTION_START = "09:30"
SCHEDULE_EXECUTION_END = "15:30"
SCHEDULE_POSTCLOSE_FEEDBACK = "16:15"  # no execution
SCHEDULE_TRACE_CLEANUP = "00:00"


# ---------------------------------------------------------------------------
# Risk and execution controls
# ---------------------------------------------------------------------------
MIN_CONFIDENCE = 0.65
MAX_POSITION_PCT = 0.10
MAX_TOTAL_EXPOSURE_PCT = 0.60
STOP_LOSS_PCT = -0.05
TAKE_PROFIT_PCT = 0.15
TRAILING_STOP_PCT = 0.03
MAX_DAILY_TRADES = 10
MAX_SINGLE_ORDER_USD = 5000.0
COOLDOWN_AFTER_LOSS_MINUTES = 30
MAX_CORRELATED_POSITIONS = 3
MAX_DRAWDOWN_PCT = -0.15
POSITION_SCALE_IN_STEPS = 3
SCALE_IN_INTERVAL_MINUTES = 60

MARKET_HOURS_ONLY = True
DROP_DECISIONS_WHEN_MARKET_CLOSED = True
REQUIRE_LLM_CONFIRMATION_FOR_TRADES = True
KILL_SWITCH_FORCED_LIQUIDATION = False


# ---------------------------------------------------------------------------
# Strategy behavior
# ---------------------------------------------------------------------------
STRATEGY_WEIGHTS = {
    "fundamental": 0.35,
    "momentum": 0.20,
    "event_driven": 0.20,
    "sentiment": 0.15,
    "mean_reversion": 0.10,
}

ENABLE_AUTO_WEIGHT_REBALANCE = (
    os.getenv("ENABLE_AUTO_WEIGHT_REBALANCE", "false").lower() == "true"
)
AUTO_WEIGHT_REBALANCE_ONLY_AT_CLOSE = True


# ---------------------------------------------------------------------------
# Data source settings
# ---------------------------------------------------------------------------
SEC_FILING_TYPES = ["10-K", "10-Q", "8-K"]
SEC_MAX_FILINGS_PER_TICKER = 3

NEWS_LOOKBACK_HOURS = 72
NEWS_MAX_ARTICLES_PER_TICKER = 15

TRANSCRIPT_LOOKBACK_QUARTERS = 2

SOCIAL_SUBREDDITS = ["wallstreetbets", "stocks", "investing", "options"]
SOCIAL_LOOKBACK_HOURS = 48
SOCIAL_MIN_UPVOTES = 50
ENABLE_STOCKTWITS = os.getenv("ENABLE_STOCKTWITS", "false").lower() == "true"

TECHNICAL_LOOKBACK_DAYS = 90


# ---------------------------------------------------------------------------
# Cost controls
# ---------------------------------------------------------------------------
RUN_COST_TARGET_USD = 0.50
RUN_COST_ALERT_THRESHOLD_USD = 1.00


# ---------------------------------------------------------------------------
# Persistence and retention
# ---------------------------------------------------------------------------
TRACE_DIR = "traces"
TRACE_RETENTION_DAYS = 90

DATA_DIR = "data"
CHECKPOINT_DB_PATH = os.getenv("CHECKPOINT_DB_PATH", "data/checkpoints.db")
AUDIT_DB_PATH = os.getenv("AUDIT_DB_PATH", "data/trading.db")

REDIS_OPTIONAL = True
CHECKPOINT_BACKEND_PRIMARY = "sqlite"
CHECKPOINT_BACKEND_CACHE_LAYER = "redis"


# ---------------------------------------------------------------------------
# Sector mapping fallback (Alpaca metadata first)
# ---------------------------------------------------------------------------
TICKER_SECTOR_MAP = {
    "AAPL": "technology",
    "MSFT": "technology",
    "GOOGL": "communications",
    "AMZN": "consumer",
    "NVDA": "technology",
}


# ---------------------------------------------------------------------------
# Backtesting
# ---------------------------------------------------------------------------
BACKTEST_FILL_TIMING = os.getenv("BACKTEST_FILL_TIMING", "next_bar_open")
BACKTEST_ALLOWED_FILL_TIMINGS = {"next_bar_open", "same_bar_close"}
BACKTEST_SLIPPAGE_PCT_PER_LEG = 0.0005  # 0.05%
BACKTEST_COMMISSION_USD_PER_ORDER = 1.0


def validate_config() -> None:
    """Validate startup configuration invariants."""
    total_weight = sum(STRATEGY_WEIGHTS.values())
    if abs(total_weight - 1.0) > 1e-9:
        raise ValueError(f"STRATEGY_WEIGHTS must sum to 1.0, got {total_weight}")

    if BACKTEST_FILL_TIMING not in BACKTEST_ALLOWED_FILL_TIMINGS:
        allowed = ", ".join(sorted(BACKTEST_ALLOWED_FILL_TIMINGS))
        raise ValueError(
            f"BACKTEST_FILL_TIMING must be one of [{allowed}], got {BACKTEST_FILL_TIMING}"
        )
