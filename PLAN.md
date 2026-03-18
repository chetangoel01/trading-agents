# Fintech Agentic Trading System — Complete Technical Blueprint

---

## 1. Project Overview

### 1.1 What This Is
A multi-agent autonomous trading system built on LangGraph that ingests financial data from every meaningful source (SEC filings, earnings transcripts, market news, social sentiment, technical indicators), extracts actionable signals, synthesizes investment theses, makes trading decisions with institutional-grade risk management, executes trades via Alpaca, monitors positions in real-time, and continuously learns from outcomes — all orchestrated through a typed shared state with full observability.

### 1.2 Why It Matters (Portfolio Positioning)
This project demonstrates: agentic orchestration (LangGraph), multi-model routing (OpenRouter), structured extraction from unstructured data, real-time API integration, risk management as code, event-driven architecture, and end-to-end system design — the exact skill set targeted by ElevenLabs, Plaid, and similar companies hiring for AI/LLM engineering roles.

### 1.3 Core Design Principles
- **State is the source of truth**: Every agent reads from and writes to a single Pydantic schema. No agent-to-agent side channels.
- **Fail loudly, degrade gracefully**: Every external call has retries, timeouts, and fallback behavior. If a data source fails, the pipeline continues with reduced confidence, not a crash.
- **Risk rules are non-negotiable**: Hardcoded guardrails in config. No LLM can override position sizing, stop-loss, or confidence thresholds.
- **Reproducible decisions**: Every run produces a full trace log that can be replayed and audited.
- **Everything is extensible**: New data sources, new strategies, new asset classes — the architecture never boxes us in. Adding a new agent is adding a node and an edge.

---

## 2. Architecture

### 2.1 High-Level Data Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           ORCHESTRATOR (LangGraph)                           │
│                                                                              │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────────┐      │
│  │  SEC      │ │  News    │ │ Earnings  │ │ Social   │ │  Technical   │      │
│  │  Fetcher  │ │  Fetcher │ │ Transcript│ │ Sentiment│ │  Indicators  │      │
│  │  Agent    │ │  Agent   │ │ Fetcher   │ │ Agent    │ │  Agent       │      │
│  └────┬─────┘ └────┬─────┘ └─────┬─────┘ └────┬─────┘ └──────┬───────┘      │
│       │            │              │             │              │              │
│       └────────────┴──────┬───────┴─────────────┴──────────────┘              │
│                           ▼                                                  │
│                  ┌───────────────┐                                            │
│                  │  Extraction   │  ← Qwen3-Coder via OpenRouter             │
│                  │  Agent        │                                            │
│                  └───────┬───────┘                                            │
│                          ▼                                                   │
│                  ┌───────────────┐                                            │
│                  │  Synthesis    │  ← Claude Sonnet via OpenRouter            │
│                  │  Agent        │                                            │
│                  └───────┬───────┘                                            │
│                          ▼                                                   │
│                  ┌───────────────┐                                            │
│                  │  Strategy     │  ← Multi-strategy engine                   │
│                  │  Engine       │                                            │
│                  └───────┬───────┘                                            │
│                          ▼                                                   │
│                  ┌───────────────┐                                            │
│                  │  Decision     │  ← Claude Sonnet via OpenRouter            │
│                  │  Agent        │                                            │
│                  └───────┬───────┘                                            │
│                          ▼                                                   │
│                  ┌───────────────┐                                            │
│                  │  Execution    │  ← Alpaca (paper → live migration path)    │
│                  │  Agent        │                                            │
│                  └───────┬───────┘                                            │
│                          ▼                                                   │
│                  ┌───────────────┐                                            │
│                  │  Monitor      │  ← Real-time position tracking             │
│                  │  Agent        │                                            │
│                  └───────┬───────┘                                            │
│                          ▼                                                   │
│                  ┌───────────────┐                                            │
│                  │  Feedback     │  ← Outcome tracking + strategy tuning      │
│                  │  Loop Agent   │                                            │
│                  └───────┬───────┘                                            │
│                          ▼                                                   │
│                  ┌───────────────┐                                            │
│                  │  Formatter    │  ← Reports, alerts, dashboard feed         │
│                  │  Agent        │                                            │
│                  └───────────────┘                                            │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │                       SHARED STATE (Pydantic)                          │   │
│  │  raw_data → signals → thesis → strategy → decision → orders → outcomes │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │                       EVENT BUS (async)                                │   │
│  │  market_open | price_alert | stop_triggered | news_breaking | schedule │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Project Directory Structure

```
fintech-agent/
├── .env                            # API keys (gitignored)
├── .env.example                    # Template with placeholder values
├── .gitignore
├── README.md
├── requirements.txt
├── pyproject.toml                  # Project metadata + tool config
├── Dockerfile                      # Containerized deployment
├── docker-compose.yml              # Full stack (app + redis + dashboard)
│
├── config.py                       # All constants, thresholds, model routing
├── state.py                        # Pydantic shared state schema
├── graph.py                        # LangGraph graph definition + edges
├── main.py                         # Entry point / CLI runner
├── scheduler.py                    # Continuous mode: cron + event triggers
│
├── agents/
│   ├── __init__.py
│   ├── base.py                     # Base agent class with retry/logging
│   │
│   ├── fetchers/
│   │   ├── __init__.py
│   │   ├── sec.py                  # SEC EDGAR fetcher
│   │   ├── news.py                 # Finnhub + RSS news fetcher
│   │   ├── transcript.py           # Earnings call transcript fetcher
│   │   ├── social.py               # Reddit/Twitter/StockTwits sentiment
│   │   └── market_data.py          # Price history, volume, technicals
│   │
│   ├── extraction.py               # Structured signal extraction (Qwen3)
│   ├── synthesis.py                # Thesis generation (Claude Sonnet)
│   ├── strategy.py                 # Multi-strategy engine
│   ├── decision.py                 # Trade decision engine (Claude Sonnet)
│   ├── execution.py                # Alpaca order placement
│   ├── monitor.py                  # Position monitoring + stop/take-profit
│   ├── feedback.py                 # Outcome tracking + confidence recalibration
│   └── formatter.py                # Reports, alerts, dashboard data
│
├── strategies/
│   ├── __init__.py
│   ├── base.py                     # Strategy interface
│   ├── fundamental.py              # Long-term value based on financials
│   ├── momentum.py                 # Price/volume momentum signals
│   ├── event_driven.py             # Trade around catalysts (earnings, FDA, etc.)
│   ├── mean_reversion.py           # Oversold/overbought reversals
│   └── sentiment.py                # Social + news sentiment plays
│
├── models/
│   ├── __init__.py
│   ├── signals.py                  # Signal Pydantic models
│   ├── thesis.py                   # Thesis Pydantic models
│   ├── orders.py                   # Order Pydantic models
│   ├── portfolio.py                # Portfolio state models
│   └── outcomes.py                 # Trade outcome + feedback models
│
├── utils/
│   ├── __init__.py
│   ├── llm.py                      # OpenRouter client wrapper
│   ├── rate_limiter.py             # Token bucket rate limiter
│   ├── retry.py                    # Exponential backoff decorator
│   ├── logger.py                   # Structured JSON logger
│   ├── token_counter.py            # tiktoken-based token budgeting
│   └── cache.py                    # Redis-backed response cache
│
├── events/
│   ├── __init__.py
│   ├── bus.py                      # Async event bus
│   ├── handlers.py                 # Event → pipeline trigger mappings
│   └── sources.py                  # Market open/close, price alerts, schedules
│
├── dashboard/
│   ├── app.py                      # FastAPI backend for dashboard
│   ├── ws.py                       # WebSocket for live updates
│   └── frontend/                   # React dashboard (served by FastAPI)
│       ├── index.html
│       ├── App.jsx
│       └── components/
│           ├── PortfolioView.jsx
│           ├── TraceTimeline.jsx
│           ├── ThesisCard.jsx
│           └── AlertFeed.jsx
│
├── notifications/
│   ├── __init__.py
│   ├── slack.py                    # Slack webhook alerts
│   ├── email.py                    # Email notifications
│   └── templates/                  # Alert message templates
│
├── backtesting/
│   ├── __init__.py
│   ├── engine.py                   # Historical replay engine
│   ├── data_loader.py              # Load historical price + filing data
│   └── metrics.py                  # Sharpe ratio, drawdown, win rate, etc.
│
├── evals/
│   ├── __init__.py
│   ├── conftest.py                 # Pytest fixtures (mock state, etc.)
│   ├── test_extraction.py          # Extraction accuracy tests
│   ├── test_synthesis.py           # Thesis quality tests
│   ├── test_decision.py            # Decision logic tests
│   ├── test_risk_rules.py          # Risk constraint enforcement
│   ├── test_strategies.py          # Strategy signal generation tests
│   ├── test_feedback.py            # Feedback loop accuracy tests
│   ├── test_graph.py               # End-to-end graph run tests
│   └── fixtures/
│       ├── sample_10k.txt          # Sample SEC filing snippet
│       ├── sample_news.json        # Sample news articles
│       ├── sample_transcript.txt   # Sample earnings call
│       ├── sample_social.json      # Sample Reddit/Twitter posts
│       └── sample_outcomes.json    # Historical trade outcomes
│
├── traces/                         # Run trace logs (gitignored)
│   └── .gitkeep
│
└── docs/
    ├── ARCHITECTURE.md
    ├── SETUP.md
    ├── STRATEGIES.md               # Strategy documentation
    ├── DECISIONS.md                 # Architecture Decision Records
    └── RUNBOOK.md                  # Ops guide: how to deploy, monitor, recover
```

---

## 3. Configuration Layer — `config.py`

### 3.1 Full Configuration Spec

```python
import os
from dotenv import load_dotenv
from enum import Enum

load_dotenv()

# ──────────────────────────────────────────────
# API Credentials
# ──────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT")  # Required by SEC: "Name email@example.com"

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# ──────────────────────────────────────────────
# Model Routing
# ──────────────────────────────────────────────
class ModelRole(str, Enum):
    EXTRACTION = "extraction"        # Fast structured output
    SYNTHESIS = "synthesis"          # Deep reasoning
    DECISION = "decision"            # Critical judgment calls
    SENTIMENT = "sentiment"          # Social media parsing
    FEEDBACK = "feedback"            # Outcome analysis

MODEL_MAP = {
    ModelRole.EXTRACTION: "qwen/qwen3-coder",
    ModelRole.SYNTHESIS: "anthropic/claude-sonnet-4-5",
    ModelRole.DECISION: "anthropic/claude-sonnet-4-5",
    ModelRole.SENTIMENT: "qwen/qwen3-coder",
    ModelRole.FEEDBACK: "anthropic/claude-sonnet-4-5",
}

# Fallback chain: if primary model fails, try these in order
MODEL_FALLBACKS = {
    ModelRole.EXTRACTION: ["anthropic/claude-sonnet-4-5"],
    ModelRole.SYNTHESIS: ["qwen/qwen3-coder"],
    ModelRole.DECISION: ["anthropic/claude-sonnet-4-5"],
    ModelRole.SENTIMENT: ["anthropic/claude-sonnet-4-5"],
    ModelRole.FEEDBACK: ["qwen/qwen3-coder"],
}

# Per-model token limits
MODEL_MAX_TOKENS = {
    "qwen/qwen3-coder": 8192,
    "anthropic/claude-sonnet-4-5": 8192,
}

# Temperature per role
MODEL_TEMPERATURE = {
    ModelRole.EXTRACTION: 0.0,       # Deterministic
    ModelRole.SYNTHESIS: 0.3,        # Some reasoning flex
    ModelRole.DECISION: 0.1,         # Mostly deterministic
    ModelRole.SENTIMENT: 0.0,        # Deterministic
    ModelRole.FEEDBACK: 0.2,         # Some analysis flex
}

# ──────────────────────────────────────────────
# Risk Management (HARDCODED — no LLM override)
# ──────────────────────────────────────────────
MIN_CONFIDENCE = 0.65               # Below this → always HOLD
MAX_POSITION_PCT = 0.10             # Max 10% of portfolio per ticker
MAX_TOTAL_EXPOSURE_PCT = 0.60       # Max 60% of portfolio in equities
STOP_LOSS_PCT = -0.05               # Trigger sell at -5%
TAKE_PROFIT_PCT = 0.15              # Trigger sell at +15%
TRAILING_STOP_PCT = 0.03            # Trailing stop at 3% below peak
MAX_DAILY_TRADES = 10               # Circuit breaker
MAX_SINGLE_ORDER_USD = 5000.0       # Per-order dollar cap
COOLDOWN_AFTER_LOSS_MINUTES = 30    # Wait period after a stop-loss triggers
MAX_CORRELATED_POSITIONS = 3        # Max tickers in same sector
MAX_DRAWDOWN_PCT = -0.15            # Kill switch: halt all trading at -15% drawdown
POSITION_SCALE_IN_STEPS = 3         # Scale into positions over N orders
SCALE_IN_INTERVAL_MINUTES = 60      # Time between scale-in orders

# ──────────────────────────────────────────────
# Strategy Weights (adjustable, sum to 1.0)
# ──────────────────────────────────────────────
STRATEGY_WEIGHTS = {
    "fundamental": 0.35,
    "momentum": 0.20,
    "event_driven": 0.20,
    "sentiment": 0.15,
    "mean_reversion": 0.10,
}

# ──────────────────────────────────────────────
# Data Source Configuration
# ──────────────────────────────────────────────
SEC_FILING_TYPES = ["10-K", "10-Q", "8-K"]
SEC_MAX_FILINGS_PER_TICKER = 3
SEC_BASE_URL = "https://efts.sec.gov/LATEST/search-index"
EDGAR_FULL_TEXT_URL = "https://www.sec.gov/Archives/edgar/data"

NEWS_LOOKBACK_HOURS = 72
NEWS_MAX_ARTICLES_PER_TICKER = 15
NEWS_RSS_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline",
]

TRANSCRIPT_LOOKBACK_QUARTERS = 2

SOCIAL_SUBREDDITS = ["wallstreetbets", "stocks", "investing", "options"]
SOCIAL_LOOKBACK_HOURS = 48
SOCIAL_MIN_UPVOTES = 50             # Filter noise

TECHNICAL_LOOKBACK_DAYS = 90
TECHNICAL_INDICATORS = [
    "SMA_20", "SMA_50", "SMA_200",  # Moving averages
    "RSI_14",                        # Relative strength
    "MACD",                          # Trend + momentum
    "BBANDS",                        # Bollinger bands (mean reversion)
    "VWAP",                          # Volume-weighted average price
    "ATR_14",                        # Average true range (volatility)
    "OBV",                           # On-balance volume
]

# ──────────────────────────────────────────────
# Rate Limiting
# ──────────────────────────────────────────────
SEC_REQUESTS_PER_SECOND = 10
FINNHUB_REQUESTS_PER_MINUTE = 60
OPENROUTER_REQUESTS_PER_MINUTE = 100
REDDIT_REQUESTS_PER_MINUTE = 30

# ──────────────────────────────────────────────
# Caching
# ──────────────────────────────────────────────
CACHE_TTL_SEC_FILINGS = 86400       # 24 hours (filings don't change)
CACHE_TTL_NEWS = 3600               # 1 hour
CACHE_TTL_TRANSCRIPTS = 86400       # 24 hours
CACHE_TTL_SOCIAL = 1800             # 30 minutes (fast moving)
CACHE_TTL_MARKET_DATA = 300         # 5 minutes

# ──────────────────────────────────────────────
# Operational
# ──────────────────────────────────────────────
TRACE_DIR = "traces"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
RUN_MODE = os.getenv("RUN_MODE", "single")  # "single" | "continuous" | "backtest"
WATCHLIST = os.getenv("WATCHLIST", "AAPL,MSFT,GOOGL,AMZN,NVDA").split(",")
CONTINUOUS_INTERVAL_MINUTES = 30
DASHBOARD_PORT = 8000
ENABLE_NOTIFICATIONS = os.getenv("ENABLE_NOTIFICATIONS", "false").lower() == "true"
```

### 3.2 `.env.example`

```
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

ALPACA_API_KEY=PK...
ALPACA_SECRET_KEY=...
ALPACA_BASE_URL=https://paper-api.alpaca.markets

FINNHUB_API_KEY=...
SEC_USER_AGENT=YourName your@email.com

REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...

SLACK_WEBHOOK_URL=https://hooks.slack.com/...
REDIS_URL=redis://localhost:6379

LOG_LEVEL=INFO
RUN_MODE=single
WATCHLIST=AAPL,MSFT,GOOGL,AMZN,NVDA
ENABLE_NOTIFICATIONS=false
```

---

## 4. Shared State — `state.py`

Every agent reads from and writes to this schema. The state is a TypedDict for LangGraph compatibility, with Pydantic models for each nested structure.

### 4.1 Core State Schema

```python
from __future__ import annotations
from typing import TypedDict, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────
class SignalDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"

class ActionType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    SCALE_IN = "scale_in"            # Partial position entry
    SCALE_OUT = "scale_out"          # Partial position exit
    HEDGE = "hedge"                  # Protective position

class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class DataSourceType(str, Enum):
    SEC_FILING = "sec_filing"
    NEWS_ARTICLE = "news_article"
    EARNINGS_TRANSCRIPT = "earnings_transcript"
    SOCIAL_POST = "social_post"
    TECHNICAL_INDICATOR = "technical_indicator"

class FilingType(str, Enum):
    TEN_K = "10-K"
    TEN_Q = "10-Q"
    EIGHT_K = "8-K"

class StrategyType(str, Enum):
    FUNDAMENTAL = "fundamental"
    MOMENTUM = "momentum"
    EVENT_DRIVEN = "event_driven"
    SENTIMENT = "sentiment"
    MEAN_REVERSION = "mean_reversion"

class OutcomeResult(str, Enum):
    WIN = "win"                      # Closed with profit
    LOSS = "loss"                    # Closed with loss
    STOPPED_OUT = "stopped_out"      # Hit stop-loss
    TOOK_PROFIT = "took_profit"      # Hit take-profit
    TRAILING_STOPPED = "trailing_stopped"
    OPEN = "open"                    # Still holding


# ──────────────────────────────────────────────
# Raw Data Models (Fetcher output)
# ──────────────────────────────────────────────
class RawDocument(BaseModel):
    """A single fetched document before extraction."""
    source_type: DataSourceType
    ticker: str
    title: str
    content: str
    url: str
    published_at: Optional[datetime] = None
    filing_type: Optional[FilingType] = None
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    content_hash: str                    # SHA-256 for dedup
    truncated: bool = False
    metadata: dict = {}                  # Source-specific extras (upvotes, author, etc.)


# ──────────────────────────────────────────────
# Technical Data Models
# ──────────────────────────────────────────────
class TechnicalSnapshot(BaseModel):
    """Technical indicators for a single ticker at a point in time."""
    ticker: str
    timestamp: datetime
    price: float
    volume: int
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    rsi_14: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    bbands_upper: Optional[float] = None
    bbands_middle: Optional[float] = None
    bbands_lower: Optional[float] = None
    vwap: Optional[float] = None
    atr_14: Optional[float] = None
    obv: Optional[float] = None
    # Derived signals
    price_vs_sma_200: Optional[str] = None  # "above" | "below"
    rsi_zone: Optional[str] = None          # "oversold" | "neutral" | "overbought"
    macd_crossover: Optional[str] = None    # "bullish" | "bearish" | "none"
    bbands_position: Optional[str] = None   # "above_upper" | "middle" | "below_lower"


# ──────────────────────────────────────────────
# Extracted Signal Models (Extraction output)
# ──────────────────────────────────────────────
class FinancialMetric(BaseModel):
    """A single extracted financial data point."""
    name: str                            # e.g., "revenue", "gross_margin"
    value: float
    unit: str                            # e.g., "USD_millions", "percent"
    period: str                          # e.g., "Q3_2025", "FY_2025"
    yoy_change: Optional[float] = None
    beat_estimate: Optional[bool] = None # Did this beat analyst consensus?

class SentimentSignal(BaseModel):
    """Extracted sentiment from a document."""
    direction: SignalDirection
    confidence: float = Field(ge=0.0, le=1.0)
    key_phrase: str
    context: str
    source_credibility: float = Field(ge=0.0, le=1.0, default=0.5)

class RiskFactor(BaseModel):
    """An identified risk from filings or news."""
    description: str
    severity: float = Field(ge=0.0, le=1.0)
    category: str                        # regulatory, competition, macro, operational, financial, legal
    is_new: bool = False                 # First time this risk appeared?

class ExtractedSignal(BaseModel):
    """All structured data extracted from a single document."""
    source_doc_hash: str
    ticker: str
    source_type: DataSourceType
    metrics: list[FinancialMetric] = []
    sentiments: list[SentimentSignal] = []
    risks: list[RiskFactor] = []
    key_events: list[str] = []
    management_guidance: Optional[str] = None
    insider_activity: Optional[str] = None      # "buying" | "selling" | "none"
    extraction_model: str
    extraction_latency_ms: int
    extracted_at: datetime = Field(default_factory=datetime.utcnow)


# ──────────────────────────────────────────────
# Strategy Signal Models
# ──────────────────────────────────────────────
class StrategySignal(BaseModel):
    """Output from a single strategy for a single ticker."""
    strategy: StrategyType
    ticker: str
    direction: SignalDirection
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    time_horizon: str                    # "intraday" | "days" | "weeks" | "months"
    suggested_entry: Optional[float] = None
    suggested_exit: Optional[float] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ──────────────────────────────────────────────
# Thesis Model (Synthesis output)
# ──────────────────────────────────────────────
class TickerThesis(BaseModel):
    """Synthesized investment thesis for a single ticker."""
    ticker: str
    direction: SignalDirection
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str
    bull_case: str
    bear_case: str
    key_catalysts: list[str]
    key_risks: list[str]
    strategy_signals: list[StrategySignal]      # What each strategy said
    dominant_strategy: StrategyType              # Which strategy carried the thesis
    data_freshness_hours: float
    signal_count: int
    conflicting_signals: int
    sector: str                                 # For correlation tracking
    synthesis_model: str
    synthesis_latency_ms: int
    synthesized_at: datetime = Field(default_factory=datetime.utcnow)


# ──────────────────────────────────────────────
# Decision Model (Decision output)
# ──────────────────────────────────────────────
class TradeDecision(BaseModel):
    """A single trade decision for one ticker."""
    ticker: str
    action: ActionType
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    position_size_pct: float
    position_size_usd: float
    entry_price_limit: Optional[float] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    trailing_stop_pct: Optional[float] = None
    scale_in_plan: Optional[list[dict]] = None  # [{"pct": 0.33, "trigger": "immediate"}, ...]
    strategy_attribution: StrategyType          # Which strategy drove this
    risk_checks_passed: list[str]
    risk_checks_failed: list[str]
    correlation_check: Optional[str] = None     # "passed" | "too_correlated"
    decision_model: str
    decision_latency_ms: int
    decided_at: datetime = Field(default_factory=datetime.utcnow)


# ──────────────────────────────────────────────
# Order Model (Execution output)
# ──────────────────────────────────────────────
class OrderRecord(BaseModel):
    """Record of a placed or attempted order."""
    ticker: str
    action: ActionType
    quantity: int
    order_type: str                      # "market" | "limit" | "stop" | "trailing_stop"
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    trailing_pct: Optional[float] = None
    alpaca_order_id: Optional[str] = None
    status: OrderStatus
    filled_price: Optional[float] = None
    filled_quantity: Optional[int] = None
    filled_at: Optional[datetime] = None
    rejected_reason: Optional[str] = None
    scale_in_step: Optional[int] = None  # Which step in scale-in plan (1, 2, 3...)
    submitted_at: datetime = Field(default_factory=datetime.utcnow)


# ──────────────────────────────────────────────
# Portfolio Snapshot (Monitor output)
# ──────────────────────────────────────────────
class PositionSnapshot(BaseModel):
    """Current state of a single position."""
    ticker: str
    quantity: int
    avg_entry_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    peak_price: float                    # For trailing stop
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    trailing_stop_price: Optional[float] = None
    triggered_exit: Optional[str] = None
    holding_duration_hours: float
    sector: str

class PortfolioSnapshot(BaseModel):
    """Full portfolio state at a point in time."""
    cash: float
    equity: float
    total_value: float
    positions: list[PositionSnapshot]
    daily_trades_count: int
    total_exposure_pct: float
    sector_exposure: dict[str, float]    # sector → % of portfolio
    max_drawdown_pct: float              # Current drawdown from peak
    peak_portfolio_value: float
    last_loss_at: Optional[datetime] = None
    snapshot_at: datetime = Field(default_factory=datetime.utcnow)


# ──────────────────────────────────────────────
# Feedback / Outcome Models
# ──────────────────────────────────────────────
class TradeOutcome(BaseModel):
    """Completed trade with result analysis."""
    ticker: str
    action: ActionType
    entry_price: float
    exit_price: float
    quantity: int
    pnl_usd: float
    pnl_pct: float
    result: OutcomeResult
    holding_duration_hours: float
    strategy_attribution: StrategyType
    thesis_confidence_at_entry: float
    exit_reason: str                     # "stop_loss" | "take_profit" | "trailing_stop" | "manual" | "thesis_invalidated"
    opened_at: datetime
    closed_at: datetime

class StrategyPerformance(BaseModel):
    """Rolling performance metrics for a single strategy."""
    strategy: StrategyType
    total_trades: int
    win_rate: float
    avg_pnl_pct: float
    max_drawdown_pct: float
    sharpe_ratio: Optional[float] = None
    recommended_weight_adjustment: float  # +/- from current weight
    period_start: datetime
    period_end: datetime

class FeedbackState(BaseModel):
    """Accumulated feedback data for strategy tuning."""
    outcomes: list[TradeOutcome] = []
    strategy_performance: list[StrategyPerformance] = []
    confidence_calibration: dict[str, float] = {}  # strategy → calibration factor
    last_rebalance_at: Optional[datetime] = None


# ──────────────────────────────────────────────
# Run Metadata
# ──────────────────────────────────────────────
class RunMetadata(BaseModel):
    """Metadata about the current pipeline run."""
    run_id: str
    started_at: datetime
    tickers: list[str]
    trigger: str                         # "scheduled" | "manual" | "event" | "price_alert"
    run_mode: str                        # "single" | "continuous" | "backtest"
    completed_nodes: list[str] = []
    errors: list[dict] = []
    warnings: list[dict] = []
    total_latency_ms: Optional[int] = None
    total_cost_usd: float = 0.0


# ──────────────────────────────────────────────
# LangGraph State (Top-Level TypedDict)
# ──────────────────────────────────────────────
class AgentState(TypedDict):
    """Top-level state passed through the LangGraph graph."""

    # Run context
    metadata: RunMetadata

    # Stage 1: Raw data
    raw_documents: list[RawDocument]
    technical_data: list[TechnicalSnapshot]

    # Stage 2: Extracted signals
    extracted_signals: list[ExtractedSignal]

    # Stage 3: Strategy signals
    strategy_signals: list[StrategySignal]

    # Stage 4: Synthesized theses
    theses: list[TickerThesis]

    # Stage 5: Trade decisions
    decisions: list[TradeDecision]

    # Stage 6: Placed orders
    orders: list[OrderRecord]

    # Stage 7: Portfolio state
    portfolio: PortfolioSnapshot

    # Stage 8: Feedback
    feedback: FeedbackState

    # Final output
    formatted_report: Optional[str]
```

### 4.2 State Invariants (enforced at graph edges)

| Invariant | When Checked | What Happens on Failure |
|-----------|-------------|------------------------|
| `len(raw_documents) > 0 or len(technical_data) > 0` | After fetchers | Skip extraction, set thesis confidence=0, action=HOLD |
| Every `extracted_signal.ticker` ∈ `metadata.tickers` | After extraction | Drop orphan signals, log warning |
| `thesis.confidence` ∈ [0, 1] | After synthesis | Clamp to range, log warning |
| `decision.position_size_pct` ≤ `MAX_POSITION_PCT` | After decision | Force clamp to MAX_POSITION_PCT |
| `portfolio.daily_trades_count` ≤ `MAX_DAILY_TRADES` | Before execution | Reject order, log circuit breaker |
| `decision.position_size_usd` ≤ `MAX_SINGLE_ORDER_USD` | Before execution | Reject order |
| `portfolio.max_drawdown_pct` > `MAX_DRAWDOWN_PCT` | Before execution | KILL SWITCH: reject ALL orders, alert |
| `portfolio.total_exposure_pct` ≤ `MAX_TOTAL_EXPOSURE_PCT` | Before execution | Reduce position or reject |
| Sector concentration ≤ `MAX_CORRELATED_POSITIONS` | After decision | Force HOLD on excess correlated tickers |
| Strategy weights sum to 1.0 | At startup | Normalize or crash |

---

## 5. Agent Specifications

### 5.1 Base Agent — `agents/base.py`

Every agent inherits from this. Provides:

```python
class BaseAgent:
    """
    Responsibilities:
    - Structured logging (JSON, includes run_id + agent name)
    - Retry with exponential backoff (configurable per agent)
    - Latency measurement (start/stop timer, writes to state)
    - Error capture (catches exceptions, writes to state.metadata.errors)
    - Cost tracking (accumulates LLM cost to state.metadata.total_cost_usd)
    - Dry-run support (if RUN_MODE == "backtest", skip side effects)
    - Cache check (Redis-backed, TTL per data source)
    """

    name: str
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    timeout_seconds: float = 30.0

    def run(self, state: AgentState) -> AgentState:
        """Main entry point. Wraps _execute with retry/logging/timing."""
        ...

    def _execute(self, state: AgentState) -> AgentState:
        """Override in subclass. Pure logic."""
        raise NotImplementedError

    def _check_cache(self, key: str) -> Optional[Any]:
        """Check Redis cache before fetching."""
        ...

    def _set_cache(self, key: str, value: Any, ttl: int):
        """Cache result with TTL."""
        ...
```

### 5.2 SEC Fetcher — `agents/fetchers/sec.py`

**Purpose**: Fetch recent SEC filings (10-K, 10-Q, 8-K) for each ticker.

**Input**: `state.metadata.tickers`
**Output**: Appends to `state.raw_documents`

**Detailed Logic**:
1. For each ticker in `state.metadata.tickers`:
   a. Check Redis cache for `sec:{ticker}:{filing_type}` — skip if fresh
   b. Query SEC EDGAR full-text search API: `https://efts.sec.gov/LATEST/search-index?q="{ticker}"&dateRange=custom&startdt={90_days_ago}&enddt={today}&forms={10-K,10-Q,8-K}`
   c. Parse response JSON → list of filing URLs
   d. For each filing (up to `SEC_MAX_FILINGS_PER_TICKER`):
      - Fetch the full filing text from EDGAR
      - Extract the relevant sections:
        - 10-K: Item 1A (Risk Factors), Item 7 (MD&A), Item 8 (Financial Statements)
        - 10-Q: Item 1 (Financial Statements), Item 2 (MD&A)
        - 8-K: All items (short event disclosures)
      - Truncate to 12,000 tokens (measured via tiktoken cl100k_base)
      - Compute SHA-256 hash of content
      - Create `RawDocument` and append
      - Cache with TTL = `CACHE_TTL_SEC_FILINGS`

**Rate Limiting**: 10 requests/second per SEC fair access policy. Token bucket.

**Error Handling**:
- 404 → Log "no filing found", continue
- 429 → Exponential backoff, max 3 retries
- Timeout → Log, skip this filing
- Malformed response → Log, skip
- Ticker not found in EDGAR → Log warning, skip
- Empty content → Skip, don't create RawDocument
- Duplicate content_hash → Skip (already fetched)

---

### 5.3 News Fetcher — `agents/fetchers/news.py`

**Purpose**: Fetch recent news articles from Finnhub and RSS feeds.

**Input**: `state.metadata.tickers`
**Output**: Appends to `state.raw_documents`

**Detailed Logic**:
1. **Finnhub API** — For each ticker:
   a. Check cache `news:finnhub:{ticker}`
   b. `GET /company-news?symbol={ticker}&from={72h_ago}&to={today}`
   c. For each article (up to `NEWS_MAX_ARTICLES_PER_TICKER`):
      - Fetch full article text via `httpx`
      - If paywall/403 → fall back to Finnhub summary
      - Truncate to 4,000 tokens
      - Compute SHA-256, create `RawDocument`
      - Cache with `CACHE_TTL_NEWS`

2. **RSS Feeds** — For each feed URL:
   a. Parse with `feedparser`
   b. Filter entries by ticker mention
   c. Deduplicate against Finnhub results by content_hash
   d. Same processing pipeline

**Error Handling**:
- Finnhub 403 → API key issue, log critical, skip news
- Article paywall → Use summary as fallback
- RSS feed down → Skip that feed, continue
- Empty → Skip

---

### 5.4 Earnings Transcript Fetcher — `agents/fetchers/transcript.py`

**Purpose**: Fetch recent earnings call transcripts.

**Input**: `state.metadata.tickers`
**Output**: Appends to `state.raw_documents`

**Detailed Logic**:
1. For each ticker:
   a. Check cache `transcript:{ticker}`
   b. Finnhub `GET /stock/transcripts?symbol={ticker}` → transcript list
   c. Filter to last `TRANSCRIPT_LOOKBACK_QUARTERS` quarters
   d. For each transcript:
      - Fetch full text
      - Extract: CEO remarks, CFO remarks, Q&A section
      - Truncate to 15,000 tokens
      - Compute hash, create `RawDocument`
      - Cache with `CACHE_TTL_TRANSCRIPTS`

**Error Handling**: No transcripts available → Log, skip. Garbled text → Skip.

---

### 5.5 Social Sentiment Fetcher — `agents/fetchers/social.py`

**Purpose**: Fetch social media posts mentioning watchlist tickers from Reddit and StockTwits.

**Input**: `state.metadata.tickers`
**Output**: Appends to `state.raw_documents`

**Detailed Logic**:
1. **Reddit** — For each subreddit in `SOCIAL_SUBREDDITS`:
   a. Check cache `social:reddit:{subreddit}:{ticker}`
   b. Query Reddit API: search posts mentioning `${ticker}` or `$TICKER`
   c. Filter: upvotes ≥ `SOCIAL_MIN_UPVOTES`, within `SOCIAL_LOOKBACK_HOURS`
   d. For each post:
      - Extract title + body + top 10 comments
      - Compute hash, create `RawDocument` with `metadata={"upvotes": N, "subreddit": "...", "comment_count": N}`
      - Cache with `CACHE_TTL_SOCIAL`

2. **StockTwits** (if API available):
   a. `GET /symbol/{ticker}/messages.json`
   b. Filter by bullish/bearish tags, sentiment score
   c. Same processing

**Error Handling**:
- Reddit rate limit → Back off, retry
- Subreddit private/banned → Skip
- StockTwits down → Continue without, reduce sentiment strategy weight for this run

---

### 5.6 Market Data / Technical Indicators — `agents/fetchers/market_data.py`

**Purpose**: Fetch price history and compute technical indicators.

**Input**: `state.metadata.tickers`
**Output**: Populates `state.technical_data`

**Detailed Logic**:
1. For each ticker:
   a. Check cache `technicals:{ticker}`
   b. Fetch daily OHLCV via Finnhub or Alpaca historical bars
   c. Compute all indicators in `TECHNICAL_INDICATORS`:
      - SMA: simple moving average over window
      - RSI: 14-period relative strength index
      - MACD: 12/26/9 standard settings
      - Bollinger Bands: 20-period, 2 std dev
      - VWAP: volume-weighted average price
      - ATR: 14-period average true range
      - OBV: on-balance volume
   d. Derive signals:
      - `price_vs_sma_200`: "above" if price > SMA_200, else "below"
      - `rsi_zone`: "oversold" if RSI < 30, "overbought" if RSI > 70, else "neutral"
      - `macd_crossover`: "bullish" if MACD crosses above signal, "bearish" if below
      - `bbands_position`: position relative to bands
   e. Create `TechnicalSnapshot`, cache with `CACHE_TTL_MARKET_DATA`

**Libraries**: Compute indicators using numpy/pandas directly — no heavy TA library dependency needed for these standard indicators.

---

### 5.7 Extraction Agent — `agents/extraction.py`

**Purpose**: Extract structured financial signals from raw documents using an LLM.

**Input**: `state.raw_documents`
**Output**: Populates `state.extracted_signals`

**Model**: `qwen/qwen3-coder` via OpenRouter (fast, good at structured output)

**Detailed Logic**:
1. Group `raw_documents` by ticker
2. For each document:
   a. Construct extraction prompt (see Section 8.1)
   b. Call LLM with JSON mode
   c. Parse response into `ExtractedSignal`
   d. Validate all fields (confidence in range, metrics have units)
   e. Record extraction latency + cost

**Batch Optimization**: Process concurrently with `asyncio.gather` (up to 5 concurrent). Each document gets its own LLM call (no cross-document pollution).

**Quality Checks**:
- Confidence values clamped to 0-1
- Non-numeric metric values dropped
- Source credibility assigned: SEC filings = 0.95, news (major outlet) = 0.8, social = 0.4
- Deduplicate identical signals across documents

**Error Handling**:
- Invalid JSON → Retry once with "Fix your JSON" appended
- Empty signals → Valid ExtractedSignal with empty lists
- Model timeout → Try fallback model
- Rate limit → Exponential backoff

---

### 5.8 Strategy Engine — `agents/strategy.py`

**Purpose**: Run each trading strategy independently against the extracted signals + technical data, producing strategy-specific signals.

**Input**: `state.extracted_signals`, `state.technical_data`
**Output**: Populates `state.strategy_signals`

**Detailed Logic**:
1. For each ticker:
   a. Run every active strategy (see `strategies/` directory):
      - **Fundamental**: Analyze metrics (revenue growth, margin expansion, guidance beat). Output directional signal + confidence.
      - **Momentum**: Check price vs SMAs, MACD crossover, volume trend. Buy on strong uptrend with volume confirmation.
      - **Event-Driven**: Flag upcoming catalysts (earnings in <7 days, FDA approval, M&A). High confidence if catalyst + fundamental alignment.
      - **Mean Reversion**: RSI oversold/overbought + Bollinger Band position. Counter-trend plays with tight stops.
      - **Sentiment**: Aggregate social + news sentiment. Weight by source credibility. High confidence needs alignment across multiple sources.
   b. Each strategy produces a `StrategySignal`
   c. Apply feedback-adjusted confidence calibration (from `state.feedback.confidence_calibration`)

2. Collect all strategy signals → `state.strategy_signals`

**Strategy Interface** (`strategies/base.py`):
```python
class BaseStrategy:
    strategy_type: StrategyType
    weight: float  # From STRATEGY_WEIGHTS

    def evaluate(
        self,
        ticker: str,
        signals: list[ExtractedSignal],
        technicals: Optional[TechnicalSnapshot],
        feedback: Optional[StrategyPerformance],
    ) -> StrategySignal:
        raise NotImplementedError
```

---

### 5.9 Synthesis Agent — `agents/synthesis.py`

**Purpose**: Combine all strategy signals and extracted data for a ticker into a coherent investment thesis.

**Input**: `state.extracted_signals`, `state.strategy_signals`, `state.technical_data`
**Output**: Populates `state.theses`

**Model**: `anthropic/claude-sonnet-4-5` via OpenRouter

**Detailed Logic**:
1. Group everything by ticker
2. For each ticker:
   a. Aggregate all metrics, sentiments, risks, events, strategy signals
   b. Compute signal statistics:
      - Total signals, directional breakdown
      - Weighted strategy consensus (apply `STRATEGY_WEIGHTS`)
      - Conflicting signals count
      - Data freshness
   c. Construct synthesis prompt with all data (see Section 8.2)
   d. Call LLM
   e. Parse into `TickerThesis` with `dominant_strategy` and `sector`

**Confidence Calibration**:
- If `conflicting_signals / total_signals > 0.4` → Cap confidence at 0.5
- If `data_freshness_hours > 168` (1 week) → Reduce confidence by 0.15
- If `signal_count < 3` → Reduce confidence by 0.10
- Apply strategy-specific calibration from feedback loop

**Error Handling**: LLM failures → fallback model → NEUTRAL thesis at confidence 0.0

---

### 5.10 Decision Agent — `agents/decision.py`

**Purpose**: Convert theses into concrete trade decisions, enforcing all risk rules.

**Input**: `state.theses`, `state.portfolio`, `state.feedback`
**Output**: Populates `state.decisions`

**Model**: `anthropic/claude-sonnet-4-5` via OpenRouter

**Detailed Logic**:
1. Fetch current portfolio state from Alpaca
2. For each `TickerThesis`:
   a. **Kill switch**: If `portfolio.max_drawdown_pct <= MAX_DRAWDOWN_PCT` → ALL HOLD, send alert
   b. **Confidence gate**: If `confidence < MIN_CONFIDENCE` → HOLD
   c. **Cooldown check**: If within `COOLDOWN_AFTER_LOSS_MINUTES` of last stop-loss → HOLD
   d. **Daily trade limit**: If `daily_trades_count >= MAX_DAILY_TRADES` → HOLD
   e. **Direction mapping**:
      - BULLISH + not holding → BUY (or SCALE_IN if using scale-in plan)
      - BULLISH + already holding + underwater → HOLD (don't average down in early version)
      - BULLISH + already holding + profitable → HOLD (let it ride)
      - BEARISH + holding → SELL (or SCALE_OUT if large position)
      - BEARISH + not holding → HOLD (shorting comes later)
      - NEUTRAL → HOLD
   f. **Correlation check**: Count positions in same `sector`. If ≥ `MAX_CORRELATED_POSITIONS` → HOLD
   g. **Position sizing** (for BUY/SCALE_IN):
      - `raw_size = confidence * MAX_POSITION_PCT * portfolio.total_value`
      - `capped_size = min(raw_size, MAX_SINGLE_ORDER_USD)`
      - Check total exposure: if adding this exceeds `MAX_TOTAL_EXPOSURE_PCT` → reduce or HOLD
      - Calculate quantity: `floor(capped_size / current_price)`
      - If scale-in enabled: split into `POSITION_SCALE_IN_STEPS` orders
   h. **Stop-loss / take-profit**:
      - `stop_loss_price = entry * (1 + STOP_LOSS_PCT)`
      - `take_profit_price = entry * (1 + TAKE_PROFIT_PCT)`
      - `trailing_stop_pct = TRAILING_STOP_PCT`
   i. **LLM red flag review** (for orders > $2000):
      - Pass thesis + proposed trade + portfolio context to LLM
      - If LLM flags concern → reduce position size by 50%
   j. Record all risk checks

**Critical Rule**: The LLM can suggest, but NEVER override hardcoded risk rules. Risk rules live in Python, not in prompts.

---

### 5.11 Execution Agent — `agents/execution.py`

**Purpose**: Place orders via Alpaca.

**Input**: `state.decisions` (where action ≠ HOLD)
**Output**: Populates `state.orders`

**Detailed Logic**:
1. Initialize Alpaca trading client
2. **Pre-flight**: Check market is open via `alpaca.get_clock()`
3. For each actionable decision:
   a. **Redundant risk check** (defense in depth):
      - Cash available for BUY
      - Position exists for SELL
      - Daily trade count under limit
   b. **Order construction**:
      - BUY: Market order (or limit if `entry_price_limit` set)
      - SELL: Market order for full position (or partial for SCALE_OUT)
      - Place bracket order if supported: entry + stop-loss + take-profit in one
   c. **Scale-in handling**:
      - If `scale_in_plan` exists: place only step 1 now
      - Schedule remaining steps via event bus (trigger on time or price)
   d. **Submit** via Alpaca API
   e. **Track**: Create `OrderRecord`, poll for fill (up to 30s for market orders)

**Error Handling**:
- Alpaca down → CRITICAL log, all orders REJECTED
- Insufficient funds → REJECTED
- Market closed → REJECTED with reason, queue for next open
- Rate limit → Retry with backoff

**Backtest Mode** (`RUN_MODE == "backtest"`):
- Skip API calls
- Simulate fill at current price
- Full pipeline runs, just no real orders

---

### 5.12 Monitor Agent — `agents/monitor.py`

**Purpose**: Real-time position monitoring against exit conditions.

**Input**: `state.orders`, Alpaca positions
**Output**: Updates `state.portfolio`, may trigger SELL decisions

**Detailed Logic**:
1. Fetch all positions from Alpaca
2. For each position:
   a. Calculate unrealized P&L
   b. Track `peak_price` (for trailing stop)
   c. Check stop-loss: `unrealized_pnl_pct <= STOP_LOSS_PCT` → flag exit
   d. Check take-profit: `unrealized_pnl_pct >= TAKE_PROFIT_PCT` → flag exit
   e. Check trailing stop: `current_price <= peak_price * (1 - TRAILING_STOP_PCT)` → flag exit
   f. Flagged positions → Create SELL decision, feed to execution
3. Build `PortfolioSnapshot`:
   - All position data
   - Total exposure %
   - Sector exposure breakdown
   - Current drawdown from peak
   - Update `peak_portfolio_value` if new high
4. **Kill switch check**: If `max_drawdown_pct <= MAX_DRAWDOWN_PCT` → halt all trading, send alert
5. Update `daily_trades_count`, `last_loss_at` if stop-loss triggered

---

### 5.13 Feedback Loop Agent — `agents/feedback.py`

**Purpose**: Track trade outcomes and adjust strategy confidence calibration over time.

**Input**: `state.orders` (filled), `state.portfolio`, historical outcomes
**Output**: Updates `state.feedback`

**Model**: `anthropic/claude-sonnet-4-5` via OpenRouter (for analysis)

**Detailed Logic**:
1. **Outcome Recording**:
   - For each closed position (SELL filled):
     - Calculate P&L, holding duration
     - Map back to original thesis and strategy
     - Create `TradeOutcome`
2. **Strategy Performance Calculation**:
   - For each strategy, compute rolling metrics:
     - Win rate (last 20 trades)
     - Average P&L %
     - Max drawdown
     - Sharpe ratio (if enough data)
   - Create `StrategyPerformance`
3. **Confidence Calibration**:
   - Compare thesis confidence at entry vs actual outcome
   - If a strategy consistently overestimates → reduce its confidence multiplier
   - If a strategy consistently underestimates → increase its confidence multiplier
   - Store as `confidence_calibration[strategy] = multiplier`
4. **Weight Adjustment Suggestions**:
   - If a strategy has win_rate < 0.35 over 20+ trades → suggest reducing weight
   - If a strategy has win_rate > 0.65 → suggest increasing weight
   - LLM analysis: "Given these performance metrics, what adjustments should we make?"
   - Suggestions are logged but NOT auto-applied (human reviews)
5. **Persist**: Write outcomes + performance to Redis for cross-run continuity

---

### 5.14 Formatter Agent — `agents/formatter.py`

**Purpose**: Generate human-readable reports + dashboard data + notifications.

**Input**: Entire `state`
**Output**: `state.formatted_report` + side effects (alerts, dashboard push)

**Report Output**:
```
═══════════════════════════════════════════
  Run Report — {run_id}
  {started_at} → {completed_at} ({latency}s)
  Mode: {run_mode} | Trigger: {trigger}
  Tickers: {tickers}
  Total Cost: ${total_cost_usd}
═══════════════════════════════════════════

📊 DATA COLLECTED
  SEC Filings: {count} across {tickers}
  News Articles: {count}
  Transcripts: {count}
  Social Posts: {count}
  Technical Snapshots: {count}

🔍 SIGNALS EXTRACTED
  Total: {count}
  Bullish: {count} | Bearish: {count} | Neutral: {count}

🧠 STRATEGY SIGNALS
  {For each strategy}:
  [{STRATEGY}] weight={weight} → {bullish_count}↑ {bearish_count}↓ {neutral_count}→

📝 THESES
  {For each ticker}:
  [{TICKER}] {direction} (confidence: {confidence}) via {dominant_strategy}
  {summary}
  ↑ Bull: {bull_case}
  ↓ Bear: {bear_case}
  Catalysts: {catalysts}
  Risks: {risks}

💰 DECISIONS
  {For each decision}:
  [{TICKER}] {action} — {reasoning}
  Size: ${position_size_usd} ({position_size_pct}% of portfolio)
  Stop: ${stop_loss} | Target: ${take_profit} | Trailing: {trailing}%
  Risk checks: ✓{passed} ✗{failed}
  {if correlation_check}: Correlation: {result}

📦 ORDERS
  {For each order}:
  [{TICKER}] {action} {quantity}x @ ${filled_price} — {status}
  {if scale_in}: Scale-in step {step}/{total}

📈 PORTFOLIO
  Cash: ${cash} | Equity: ${equity} | Total: ${total_value}
  Exposure: {total_exposure_pct}%
  Drawdown: {max_drawdown_pct}%
  Positions: {count}
  Daily trades: {count}/{MAX_DAILY_TRADES}
  Sector exposure: {breakdown}

🔄 FEEDBACK
  Recent win rate: {win_rate}
  Strategy performance: {summary}
  Calibration adjustments: {adjustments}

⚠️ ERRORS ({count})
  {any errors}

⚡ WARNINGS ({count})
  {any warnings}
═══════════════════════════════════════════
```

**Dashboard Push**: Format key metrics as JSON, push to FastAPI WebSocket for live dashboard.

**Notifications**: If `ENABLE_NOTIFICATIONS`:
- Order filled → Slack message
- Stop-loss triggered → Slack + email
- Kill switch activated → Slack + email + SMS
- Strategy weight adjustment suggested → Slack

---

## 6. LangGraph Graph Definition — `graph.py`

### 6.1 Graph Structure

```python
from langgraph.graph import StateGraph, START, END
from state import AgentState, ActionType

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("fetch_sec", sec_fetcher.run)
    graph.add_node("fetch_news", news_fetcher.run)
    graph.add_node("fetch_transcripts", transcript_fetcher.run)
    graph.add_node("fetch_social", social_fetcher.run)
    graph.add_node("fetch_market_data", market_data_fetcher.run)
    graph.add_node("extract", extraction_agent.run)
    graph.add_node("strategize", strategy_engine.run)
    graph.add_node("synthesize", synthesis_agent.run)
    graph.add_node("decide", decision_agent.run)
    graph.add_node("execute", execution_agent.run)
    graph.add_node("monitor", monitor_agent.run)
    graph.add_node("feedback", feedback_agent.run)
    graph.add_node("format", formatter_agent.run)

    # Parallel fetchers (fan-out from START)
    graph.add_edge(START, "fetch_sec")
    graph.add_edge(START, "fetch_news")
    graph.add_edge(START, "fetch_transcripts")
    graph.add_edge(START, "fetch_social")
    graph.add_edge(START, "fetch_market_data")

    # Fan-in: all fetchers → extraction
    graph.add_edge("fetch_sec", "extract")
    graph.add_edge("fetch_news", "extract")
    graph.add_edge("fetch_transcripts", "extract")
    graph.add_edge("fetch_social", "extract")
    graph.add_edge("fetch_market_data", "extract")

    # Linear pipeline: extract → strategize → synthesize → decide
    graph.add_edge("extract", "strategize")
    graph.add_edge("strategize", "synthesize")
    graph.add_edge("synthesize", "decide")

    # Conditional: actionable decisions → execute, else → feedback
    graph.add_conditional_edges(
        "decide",
        route_after_decision,
        {
            "execute": "execute",
            "skip_to_feedback": "feedback",
        }
    )

    graph.add_edge("execute", "monitor")
    graph.add_edge("monitor", "feedback")
    graph.add_edge("feedback", "format")
    graph.add_edge("format", END)

    return graph.compile()


def route_after_decision(state: AgentState) -> str:
    actionable = [d for d in state["decisions"] if d.action != ActionType.HOLD]
    if actionable:
        return "execute"
    return "skip_to_feedback"
```

### 6.2 State Reducers for Parallel Execution

For the parallel fetcher fan-out to work, list fields need reducers:

```python
import operator
from langgraph.graph import StateGraph

# When parallel nodes write to the same list field,
# use operator.add to merge results
class AgentState(TypedDict):
    raw_documents: Annotated[list[RawDocument], operator.add]
    technical_data: Annotated[list[TechnicalSnapshot], operator.add]
    # ... other fields with their reducers
```

---

## 7. Event-Driven Architecture — `events/`

### 7.1 Event Bus — `events/bus.py`

```python
"""
Async event bus for triggering pipeline runs and intra-run actions.

Events:
  - market_open        → Trigger morning analysis run
  - market_close       → Trigger end-of-day summary + feedback
  - price_alert        → Ticker hit a price threshold → re-evaluate
  - stop_triggered     → Position hit stop-loss → execute exit
  - news_breaking      → High-impact news detected → emergency re-analysis
  - schedule           → Cron-based periodic runs
  - scale_in_trigger   → Time/price trigger for next scale-in step

Usage:
  bus = EventBus()
  bus.subscribe("price_alert", handle_price_alert)
  await bus.emit("price_alert", {"ticker": "AAPL", "price": 195.0})
"""
```

### 7.2 Event Sources — `events/sources.py`

```python
"""
Concrete event emitters:
  - MarketClockSource: Emits market_open/close based on Alpaca clock
  - PriceAlertSource: Monitors streaming prices, emits when thresholds hit
  - ScheduleSource: Cron-like scheduling (every 30 min during market hours)
  - NewsAlertSource: Polls for high-impact news (breaking keyword detection)
"""
```

### 7.3 Scheduler — `scheduler.py`

```python
"""
Continuous mode entry point.

Loop:
  1. Wait for next event (schedule, market_open, price_alert, etc.)
  2. Build initial state from event context
  3. Run graph
  4. Log results
  5. If continuous mode: go to 1
  6. If single mode: exit

Supports:
  - Cron scheduling: "every 30 min during market hours"
  - Event-driven: react to price alerts, news, stop triggers
  - Graceful shutdown: finish current run, don't start new ones
"""
```

---

## 8. Prompt Engineering

### 8.1 Extraction Prompt Template

```
SYSTEM:
You are a financial data extraction engine. Given a financial document,
extract structured signals in EXACTLY the JSON format below. Do not
include any text outside the JSON.

OUTPUT SCHEMA:
{
  "metrics": [
    {"name": "string", "value": number, "unit": "string", "period": "string",
     "yoy_change": number|null, "beat_estimate": bool|null}
  ],
  "sentiments": [
    {"direction": "bullish|bearish|neutral", "confidence": 0.0-1.0,
     "key_phrase": "string", "context": "string"}
  ],
  "risks": [
    {"description": "string", "severity": 0.0-1.0, "category": "string",
     "is_new": bool}
  ],
  "key_events": ["string"],
  "management_guidance": "string|null",
  "insider_activity": "buying|selling|none|null"
}

RULES:
- Only extract data explicitly stated in the document.
- If a metric is mentioned without a clear number, omit it.
- Confidence reflects how clearly the signal is stated, not your opinion.
- For sentiments, key_phrase must be a direct quote under 15 words.
- Categories for risks: regulatory, competition, macro, operational, financial, legal.
- is_new = true if this risk was not mentioned in prior filings (use your judgment).
- beat_estimate = true/false only if the document explicitly compares to estimates.

USER:
Document type: {source_type}
Ticker: {ticker}
Content:
---
{content}
---

Extract all financial signals from this document.
```

### 8.2 Synthesis Prompt Template

```
SYSTEM:
You are a senior equity research analyst managing a multi-strategy fund.
Given signals from multiple data sources AND strategy-specific signals
for a single ticker, synthesize a unified investment thesis.

You must weigh conflicting signals honestly. If strategies disagree, your
confidence should reflect that uncertainty. Your job is not to pick a side
but to give the most accurate probability-weighted view.

Identify which strategy is dominant (driving the thesis) and assign a sector.

USER:
Ticker: {ticker}
Signal count: {total_signals}
Conflicting signals: {conflicting_count}
Data freshness: {freshness_hours} hours

STRATEGY SIGNALS (weighted):
{For each strategy: type, weight, direction, confidence, reasoning}

FINANCIAL METRICS:
{json_metrics}

SENTIMENTS:
{json_sentiments}

RISKS:
{json_risks}

KEY EVENTS:
{json_events}

TECHNICAL SNAPSHOT:
{json_technicals}

MANAGEMENT GUIDANCE:
{guidance}

Produce your thesis as JSON:
{
  "direction": "bullish|bearish|neutral",
  "confidence": 0.0-1.0,
  "summary": "2-3 sentences",
  "bull_case": "strongest argument for buying",
  "bear_case": "strongest argument against buying",
  "key_catalysts": ["what could move the stock up"],
  "key_risks": ["what could go wrong"],
  "dominant_strategy": "fundamental|momentum|event_driven|sentiment|mean_reversion",
  "sector": "technology|healthcare|financials|consumer|energy|industrials|utilities|materials|real_estate|communications"
}
```

### 8.3 Decision Red Flag Prompt

```
SYSTEM:
You are a risk manager reviewing a proposed trade. Find red flags the
system might have missed. Be concise and specific. Consider: portfolio
concentration, recent drawdown, conflicting signals, data staleness,
sector correlation, and position sizing.

USER:
Proposed trade:
  Ticker: {ticker} | Sector: {sector}
  Action: {action}
  Size: ${size} ({pct}% of portfolio)
  Strategy: {dominant_strategy}

Thesis:
  Direction: {direction} (confidence: {confidence})
  Summary: {summary}
  Conflicting signals: {conflicting_count}/{total_signals}

Current portfolio:
  Total: ${total_value} | Cash: ${cash}
  Drawdown: {drawdown}%
  Exposure: {exposure}%
  Sector exposure: {sector_breakdown}
  Daily trades: {count}/{max}
  Existing positions: {positions_summary}

Recent performance:
  Last 5 trades: {outcomes_summary}
  Strategy win rate: {strategy_win_rate}

Question: List red flags in 3 sentences or fewer. If clear, respond "CLEAR".
```

### 8.4 Feedback Analysis Prompt

```
SYSTEM:
You are a quantitative analyst reviewing trading strategy performance.
Given recent trade outcomes and per-strategy metrics, provide actionable
recommendations for weight adjustments and confidence calibration.

USER:
Period: {start} to {end}

Overall performance:
  Trades: {total} | Win rate: {win_rate} | Avg P&L: {avg_pnl}%
  Max drawdown: {max_dd}%

Per-strategy breakdown:
{For each strategy: trades, win_rate, avg_pnl, sharpe, current_weight}

Recent outcomes (last 10):
{For each: ticker, strategy, entry, exit, pnl, confidence_at_entry}

Questions:
1. Which strategies should have their weights adjusted? By how much?
2. Are any strategies consistently over- or under-confident?
3. Any patterns in losses (time of day, sector, holding period)?

Respond as JSON:
{
  "weight_adjustments": [{"strategy": "...", "current": 0.X, "recommended": 0.X, "reason": "..."}],
  "confidence_adjustments": [{"strategy": "...", "multiplier": 0.X, "reason": "..."}],
  "patterns": ["..."],
  "overall_recommendation": "..."
}
```

---

## 9. Utility Layer

### 9.1 OpenRouter Client — `utils/llm.py`

```python
"""
Wraps OpenRouter API calls with:
- Model routing (maps ModelRole → model string)
- Fallback chains (primary fails → try fallback models in order)
- Response parsing (JSON mode, text mode, structured Pydantic output)
- Token counting (pre-call estimation to stay under limits)
- Cost tracking (log estimated cost per call, accumulate to state)
- Retry with backoff (3 attempts, exponential)
- Request/response logging (full prompt + response for debugging)
"""

class LLMClient:
    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=OPENROUTER_BASE_URL,
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            timeout=60.0,
        )
        self.total_cost_usd = 0.0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    async def complete(self, role: ModelRole, messages: list[dict],
                       json_mode: bool = False, max_tokens: int = None) -> dict:
        """Send completion request with automatic fallback."""
        ...

    async def complete_structured(self, role: ModelRole, messages: list[dict],
                                  response_model: type[BaseModel]) -> BaseModel:
        """Complete + parse into Pydantic model. Retry on parse failure."""
        ...

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count using tiktoken."""
        ...

    def get_cost_summary(self) -> dict:
        """Return total cost, token counts, per-model breakdown."""
        ...
```

### 9.2 Rate Limiter — `utils/rate_limiter.py`

```python
"""
Token-bucket rate limiter supporting multiple named buckets.
Async-safe. Uses asyncio.Event for blocking.

Usage:
    limiter = RateLimiter()
    limiter.add_bucket("sec", rate=10, per_seconds=1)
    limiter.add_bucket("finnhub", rate=60, per_seconds=60)
    limiter.add_bucket("openrouter", rate=100, per_seconds=60)
    limiter.add_bucket("reddit", rate=30, per_seconds=60)
    await limiter.acquire("sec")  # Blocks until token available
"""
```

### 9.3 Cache — `utils/cache.py`

```python
"""
Redis-backed cache with TTL per data source.
Falls back to in-memory dict if Redis unavailable.

Usage:
    cache = Cache(redis_url=REDIS_URL)
    cached = await cache.get("sec:AAPL:10-K")
    if not cached:
        data = await fetch_from_sec(...)
        await cache.set("sec:AAPL:10-K", data, ttl=CACHE_TTL_SEC_FILINGS)

Also supports:
    - cache.invalidate("sec:AAPL:*")  # Pattern-based invalidation
    - cache.stats()                    # Hit/miss rates
"""
```

### 9.4 Token Counter — `utils/token_counter.py`

```python
"""
Wrapper around tiktoken for pre-call token budget management.

Usage:
    counter = TokenCounter(encoding="cl100k_base")
    tokens = counter.count(text)
    truncated = counter.truncate(text, max_tokens=12000)
    fits = counter.fits_in_context(messages, model_max=8192)
"""
```

---

## 10. Dashboard — `dashboard/`

### 10.1 Architecture

```
FastAPI backend (dashboard/app.py)
├── REST API: /api/portfolio, /api/runs, /api/strategies
├── WebSocket: /ws/live — pushes real-time updates
└── Static files: serves React frontend

React frontend (dashboard/frontend/)
├── PortfolioView — positions, P&L, exposure chart
├── TraceTimeline — visual timeline of a run (nodes, latency, decisions)
├── ThesisCard — per-ticker thesis with strategy breakdown
├── AlertFeed — live notifications and warnings
├── StrategyDashboard — per-strategy performance over time
└── TradeHistory — all historical trades with outcome tagging
```

### 10.2 Key Endpoints

| Endpoint | Method | Returns |
|----------|--------|---------|
| `/api/portfolio` | GET | Current `PortfolioSnapshot` |
| `/api/runs` | GET | List of recent `RunMetadata` |
| `/api/runs/{id}` | GET | Full state for a specific run |
| `/api/runs/{id}/trace` | GET | JSONL trace for a run |
| `/api/strategies` | GET | Current `StrategyPerformance` for all strategies |
| `/api/outcomes` | GET | Trade outcomes with filters (ticker, strategy, date) |
| `/ws/live` | WS | Real-time: portfolio updates, order fills, alerts |

---

## 11. Backtesting Engine — `backtesting/`

### 11.1 Architecture

The backtesting engine replays historical data through the exact same pipeline. The only difference: execution agent simulates fills instead of calling Alpaca.

```python
"""
backtesting/engine.py

Usage:
    python -m backtesting.engine --start 2025-01-01 --end 2025-12-31 --tickers AAPL,MSFT

Flow:
    1. Load historical price data + cached filings/news for date range
    2. For each trading day in range:
       a. Set state clock to that day
       b. Filter raw_documents to only those available on that date
       c. Run full graph in backtest mode (execution simulates fills)
       d. Record portfolio value, trades, outcomes
    3. Compute aggregate metrics:
       - Total return, annualized return
       - Sharpe ratio, Sortino ratio
       - Max drawdown, recovery time
       - Win rate, average win/loss size
       - Per-strategy attribution
    4. Output: performance report + equity curve data

backtesting/metrics.py:
    - sharpe_ratio(returns, risk_free_rate)
    - sortino_ratio(returns, risk_free_rate)
    - max_drawdown(equity_curve)
    - calmar_ratio(annual_return, max_drawdown)
    - win_rate(outcomes)
    - profit_factor(outcomes)
"""
```

---

## 12. Notifications — `notifications/`

### 12.1 Alert Types

| Alert | Channel | Trigger |
|-------|---------|---------|
| Order Filled | Slack | Any order status → FILLED |
| Stop-Loss Triggered | Slack + Email | Position exit via stop-loss |
| Take-Profit Hit | Slack | Position exit via take-profit |
| Kill Switch Activated | Slack + Email | Drawdown exceeds MAX_DRAWDOWN_PCT |
| Strategy Weight Suggestion | Slack | Feedback agent recommends adjustment |
| Pipeline Error | Slack | Any CRITICAL-level error in run |
| Daily Summary | Email | End-of-day portfolio + performance |

### 12.2 Templates

```python
"""
notifications/templates/

Slack messages use Block Kit for rich formatting.
Email uses simple HTML templates.
All templates are Jinja2 with state variables injected.
"""
```

---

## 13. Observability & Tracing

### 13.1 Trace File Format

Each run produces `traces/{run_id}.jsonl`. One JSON object per line:

```json
{"ts": "...", "event": "run_start", "tickers": ["AAPL","MSFT"], "trigger": "manual", "mode": "continuous"}
{"ts": "...", "event": "node_start", "node": "fetch_sec"}
{"ts": "...", "event": "cache_hit", "node": "fetch_sec", "key": "sec:AAPL:10-K"}
{"ts": "...", "event": "fetch", "node": "fetch_sec", "ticker": "AAPL", "filing_type": "10-K", "url": "...", "status": 200, "latency_ms": 450}
{"ts": "...", "event": "node_end", "node": "fetch_sec", "docs_added": 3, "latency_ms": 2100}
{"ts": "...", "event": "llm_call", "node": "extract", "model": "qwen/qwen3-coder", "input_tokens": 3200, "output_tokens": 800, "latency_ms": 1400, "cost_usd": 0.002}
{"ts": "...", "event": "strategy_signal", "node": "strategize", "ticker": "AAPL", "strategy": "fundamental", "direction": "bullish", "confidence": 0.78}
{"ts": "...", "event": "risk_check", "node": "decide", "ticker": "AAPL", "check": "confidence_gate", "passed": true}
{"ts": "...", "event": "risk_check", "node": "decide", "ticker": "AAPL", "check": "correlation", "passed": true, "sector_count": 1}
{"ts": "...", "event": "order", "node": "execute", "ticker": "AAPL", "action": "buy", "qty": 12, "status": "filled", "price": 198.50}
{"ts": "...", "event": "feedback", "node": "feedback", "strategy": "fundamental", "win_rate": 0.62, "calibration": 0.95}
{"ts": "...", "event": "run_end", "total_latency_ms": 45000, "total_cost_usd": 0.12, "orders_placed": 2}
```

### 13.2 Trace Viewer

```bash
python -m tools.trace_viewer traces/abc-123.jsonl
# Opens terminal UI with:
# - Timeline of nodes with latency bars
# - Expandable LLM calls (input/output)
# - Risk check pass/fail tree
# - Order flow visualization
```

---

## 14. Evaluation Strategy

### 14.1 Test Matrix

| Test File | What It Tests | Approach |
|-----------|--------------|----------|
| `test_extraction.py` | Signal extraction accuracy | Golden fixtures: known 10-K → expected metrics |
| `test_synthesis.py` | Thesis coherence | Known signals → thesis direction matches majority |
| `test_decision.py` | Decision logic | Unit test each risk rule independently |
| `test_risk_rules.py` | Constraint enforcement | Fuzz: random inputs → no rule violations |
| `test_strategies.py` | Strategy signal generation | Known technical data → expected signals |
| `test_feedback.py` | Calibration accuracy | Historical outcomes → correct adjustments |
| `test_graph.py` | End-to-end pipeline | Mock all APIs → full run → valid output state |

### 14.2 Example Tests

```python
def test_confidence_gate_blocks_low_confidence():
    thesis = TickerThesis(confidence=0.3, direction=SignalDirection.BULLISH, ...)
    decision = decision_agent._make_decision(thesis, portfolio)
    assert decision.action == ActionType.HOLD
    assert "confidence_gate" in decision.risk_checks_failed

def test_position_size_never_exceeds_max():
    for _ in range(100):
        thesis = random_thesis(confidence=random.uniform(0.65, 1.0))
        decision = decision_agent._make_decision(thesis, portfolio)
        if decision.action == ActionType.BUY:
            assert decision.position_size_pct <= MAX_POSITION_PCT

def test_kill_switch_halts_all_trading():
    portfolio = PortfolioSnapshot(max_drawdown_pct=-0.16, ...)  # Exceeds -15%
    thesis = TickerThesis(confidence=0.99, direction=SignalDirection.BULLISH, ...)
    decision = decision_agent._make_decision(thesis, portfolio)
    assert decision.action == ActionType.HOLD
    assert "kill_switch" in decision.risk_checks_failed

def test_correlation_blocks_excess_sector_exposure():
    portfolio = PortfolioSnapshot(
        positions=[
            PositionSnapshot(sector="technology", ...),
            PositionSnapshot(sector="technology", ...),
            PositionSnapshot(sector="technology", ...),
        ], ...
    )
    thesis = TickerThesis(sector="technology", confidence=0.9, ...)
    decision = decision_agent._make_decision(thesis, portfolio)
    assert decision.correlation_check == "too_correlated"

def test_feedback_reduces_overconfident_strategy():
    outcomes = [
        TradeOutcome(strategy_attribution=StrategyType.MOMENTUM,
                     thesis_confidence_at_entry=0.85, pnl_pct=-0.03, ...),
        # ... 10 more losses with high entry confidence
    ]
    calibration = feedback_agent._compute_calibration(outcomes)
    assert calibration[StrategyType.MOMENTUM] < 1.0  # Should reduce confidence
```

---

## 15. Development Roadmap

### Phase 1: Foundation (Week 1)
| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | Project setup, config, env, Docker skeleton | Working config, deps installed |
| 2 | `state.py` — full schema with all models | All Pydantic models validated |
| 3 | `utils/` — LLM client, rate limiter, retry, logger, cache | Working OpenRouter + Redis calls |
| 4 | SEC fetcher + news fetcher + tests | Fetches real data from EDGAR + Finnhub |
| 5 | Transcript fetcher + social fetcher + market data | All 5 fetchers working + cached |

### Phase 2: Intelligence (Week 2)
| Day | Task | Deliverable |
|-----|------|-------------|
| 6 | Extraction agent + prompt engineering | Structured signals from test fixtures |
| 7 | Strategy engine — fundamental + momentum | Strategy signals from test data |
| 8 | Strategy engine — event-driven + sentiment + mean reversion | All 5 strategies operational |
| 9 | Synthesis agent + prompt engineering | Coherent theses with strategy attribution |
| 10 | Decision agent + full risk rule engine | Decisions that respect every constraint |

### Phase 3: Execution & Monitoring (Week 3)
| Day | Task | Deliverable |
|-----|------|-------------|
| 11 | Alpaca integration — execution agent with bracket orders | Paper trades placing + filling |
| 12 | Monitor agent — stop-loss, take-profit, trailing stop | Automatic exits triggering |
| 13 | Feedback loop agent — outcome tracking + calibration | Strategy performance tracked |
| 14 | LangGraph wiring — full parallel graph with fan-out/fan-in | Complete pipeline runs end-to-end |
| 15 | Formatter + trace logging | Reports, JSONL traces, trace viewer |

### Phase 4: Infrastructure (Week 4)
| Day | Task | Deliverable |
|-----|------|-------------|
| 16 | Event bus + scheduler — continuous mode | Runs on schedule + reacts to events |
| 17 | Notifications — Slack + email alerts | Real-time alerts on trades/errors |
| 18 | Dashboard — FastAPI + React frontend | Live portfolio + trace visualization |
| 19 | Backtesting engine | Historical replay with performance metrics |
| 20 | Full evaluation suite — all test files | Comprehensive test coverage |

### Phase 5: Ship It (Week 5)
| Day | Task | Deliverable |
|-----|------|-------------|
| 21 | Docker Compose — full stack deployment | One-command deployment |
| 22 | Error handling hardening + load testing | Stable under realistic conditions |
| 23 | README + ARCHITECTURE.md + RUNBOOK.md | Portfolio-ready documentation |
| 24 | Record demo: live run with real data | Trace + report + dashboard screenshots |
| 25 | Blog post + GitHub cleanup + CI/CD | Published, polished, shipped |

---

## 16. Key Architecture Decisions (ADRs)

### ADR-001: Why LangGraph over raw asyncio?
LangGraph gives us typed state, conditional edges, parallel fan-out/fan-in, and built-in checkpointing. Raw asyncio would require reimplementing all of this.

### ADR-002: Why OpenRouter instead of direct API calls?
Single API key, model switching without code changes, built-in fallbacks, unified billing. The ~50ms latency overhead is negligible.

### ADR-003: Why Pydantic models over plain dicts?
Catch data shape bugs at write time. Auto-generates JSON schema for LLM structured output. Self-documenting.

### ADR-004: Why hardcoded risk rules over LLM-driven risk?
LLMs can be persuaded to override their own rules. Position sizing, stop-loss, and trade limits must be mathematically enforced in Python. The LLM suggests within constraints, never overrides them.

### ADR-005: Why a multi-strategy approach?
Single-strategy systems are brittle. Markets cycle between regimes (trending, mean-reverting, event-driven). A weighted multi-strategy approach with feedback-driven weight adjustment adapts to regime changes.

### ADR-006: Why Redis for caching and state persistence?
Fast key-value access, TTL support, pub/sub for event bus, and persistence across runs. The feedback loop needs cross-run memory, and Redis handles this without a full database.

### ADR-007: Why parallel fetchers from day one?
Data fetching is the bottleneck. Running 5 fetchers sequentially means 5x latency. LangGraph's fan-out makes parallel trivial, and the state reducer pattern handles merging cleanly.

### ADR-008: Why a feedback loop instead of static weights?
Markets change. A strategy that works in Q1 might fail in Q3. The feedback loop tracks per-strategy win rates and adjusts confidence calibration automatically. Weight changes are suggested (not auto-applied) to keep a human in the loop.