"""Typed shared state for LangGraph pipeline runs."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Optional, TypedDict

from pydantic import BaseModel, Field


class SignalDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class ActionType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    SCALE_IN = "scale_in"
    SCALE_OUT = "scale_out"
    HEDGE = "hedge"


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
    WIN = "win"
    LOSS = "loss"
    STOPPED_OUT = "stopped_out"
    TOOK_PROFIT = "took_profit"
    TRAILING_STOPPED = "trailing_stopped"
    OPEN = "open"


class RawDocument(BaseModel):
    source_type: DataSourceType
    ticker: str
    title: str
    content: str
    url: str
    published_at: Optional[datetime] = None
    filing_type: Optional[FilingType] = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content_hash: str
    truncated: bool = False
    metadata: dict = Field(default_factory=dict)


class TechnicalSnapshot(BaseModel):
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
    price_vs_sma_200: Optional[str] = None
    rsi_zone: Optional[str] = None
    macd_crossover: Optional[str] = None
    bbands_position: Optional[str] = None


class FinancialMetric(BaseModel):
    name: str
    value: float
    unit: str
    period: str
    yoy_change: Optional[float] = None
    beat_estimate: Optional[bool] = None


class SentimentSignal(BaseModel):
    direction: SignalDirection
    confidence: float = Field(ge=0.0, le=1.0)
    key_phrase: str
    context: str
    source_credibility: float = Field(ge=0.0, le=1.0, default=0.5)


class RiskFactor(BaseModel):
    description: str
    severity: float = Field(ge=0.0, le=1.0)
    category: str
    is_new: bool = False


class ExtractedSignal(BaseModel):
    source_doc_hash: str
    ticker: str
    source_type: DataSourceType
    metrics: list[FinancialMetric] = Field(default_factory=list)
    sentiments: list[SentimentSignal] = Field(default_factory=list)
    risks: list[RiskFactor] = Field(default_factory=list)
    key_events: list[str] = Field(default_factory=list)
    management_guidance: Optional[str] = None
    insider_activity: Optional[str] = None
    extraction_model: str
    extraction_latency_ms: int
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StrategySignal(BaseModel):
    strategy: StrategyType
    ticker: str
    direction: SignalDirection
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    time_horizon: str
    suggested_entry: Optional[float] = None
    suggested_exit: Optional[float] = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TickerThesis(BaseModel):
    ticker: str
    direction: SignalDirection
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str
    bull_case: str
    bear_case: str
    key_catalysts: list[str] = Field(default_factory=list)
    key_risks: list[str] = Field(default_factory=list)
    strategy_signals: list[StrategySignal] = Field(default_factory=list)
    dominant_strategy: StrategyType
    data_freshness_hours: float
    signal_count: int
    conflicting_signals: int
    sector: str
    synthesis_model: str
    synthesis_latency_ms: int
    synthesized_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TradeDecision(BaseModel):
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
    scale_in_plan: Optional[list[dict]] = None
    strategy_attribution: StrategyType
    risk_checks_passed: list[str] = Field(default_factory=list)
    risk_checks_failed: list[str] = Field(default_factory=list)
    correlation_check: Optional[str] = None
    decision_model: str
    decision_latency_ms: int
    decided_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class OrderRecord(BaseModel):
    ticker: str
    action: ActionType
    quantity: int
    order_type: str
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    trailing_pct: Optional[float] = None
    alpaca_order_id: Optional[str] = None
    status: OrderStatus
    filled_price: Optional[float] = None
    filled_quantity: Optional[int] = None
    filled_at: Optional[datetime] = None
    rejected_reason: Optional[str] = None
    scale_in_step: Optional[int] = None
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PositionSnapshot(BaseModel):
    ticker: str
    quantity: int
    avg_entry_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    peak_price: float
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    trailing_stop_price: Optional[float] = None
    triggered_exit: Optional[str] = None
    holding_duration_hours: float
    sector: str


class PortfolioSnapshot(BaseModel):
    cash: float = 0.0
    equity: float = 0.0
    total_value: float = 0.0
    positions: list[PositionSnapshot] = Field(default_factory=list)
    daily_trades_count: int = 0
    total_exposure_pct: float = 0.0
    sector_exposure: dict[str, float] = Field(default_factory=dict)
    max_drawdown_pct: float = 0.0
    peak_portfolio_value: float = 0.0
    last_loss_at: Optional[datetime] = None
    snapshot_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TradeOutcome(BaseModel):
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
    exit_reason: str
    opened_at: datetime
    closed_at: datetime


class StrategyPerformance(BaseModel):
    strategy: StrategyType
    total_trades: int
    win_rate: float
    avg_pnl_pct: float
    max_drawdown_pct: float
    sharpe_ratio: Optional[float] = None
    recommended_weight_adjustment: float
    period_start: datetime
    period_end: datetime


class FeedbackState(BaseModel):
    outcomes: list[TradeOutcome] = Field(default_factory=list)
    strategy_performance: list[StrategyPerformance] = Field(default_factory=list)
    confidence_calibration: dict[str, float] = Field(default_factory=dict)
    last_rebalance_at: Optional[datetime] = None


class RunMetadata(BaseModel):
    run_id: str
    started_at: datetime
    tickers: list[str]
    trigger: str
    run_mode: str
    completed_nodes: list[str] = Field(default_factory=list)
    errors: list[dict] = Field(default_factory=list)
    warnings: list[dict] = Field(default_factory=list)
    total_latency_ms: Optional[int] = None
    total_cost_usd: float = 0.0


class AgentState(TypedDict):
    metadata: RunMetadata
    raw_documents: list[RawDocument]
    technical_data: list[TechnicalSnapshot]
    extracted_signals: list[ExtractedSignal]
    strategy_signals: list[StrategySignal]
    theses: list[TickerThesis]
    decisions: list[TradeDecision]
    orders: list[OrderRecord]
    portfolio: PortfolioSnapshot
    feedback: FeedbackState
    formatted_report: Optional[str]
