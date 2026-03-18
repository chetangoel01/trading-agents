from __future__ import annotations

from datetime import UTC, datetime

from agents.decision import DecisionAgent
from config import MAX_POSITION_PCT, MAX_SINGLE_ORDER_USD, MIN_CONFIDENCE
from state import (
    AgentState,
    FeedbackState,
    PortfolioSnapshot,
    PositionSnapshot,
    RunMetadata,
    SignalDirection,
    StrategyType,
    TickerThesis,
)


def _state(thesis: TickerThesis, *, portfolio: PortfolioSnapshot) -> AgentState:
    return AgentState(
        metadata=RunMetadata(
            run_id="run-1",
            started_at=datetime.now(UTC),
            tickers=[thesis.ticker],
            trigger="manual",
            run_mode="single",
        ),
        raw_documents=[],
        technical_data=[],
        extracted_signals=[],
        strategy_signals=[],
        theses=[thesis],
        decisions=[],
        orders=[],
        portfolio=portfolio,
        feedback=FeedbackState(),
        formatted_report=None,
    )


def _thesis(*, confidence: float, direction: SignalDirection, sector: str = "technology") -> TickerThesis:
    return TickerThesis(
        ticker="AAPL",
        direction=direction,
        confidence=confidence,
        summary="summary",
        bull_case="bull",
        bear_case="bear",
        key_catalysts=["cat"],
        key_risks=["risk"],
        strategy_signals=[],
        dominant_strategy=StrategyType.FUNDAMENTAL,
        data_freshness_hours=1.0,
        signal_count=5,
        conflicting_signals=1,
        sector=sector,
        synthesis_model="test",
        synthesis_latency_ms=1,
    )


def _portfolio() -> PortfolioSnapshot:
    return PortfolioSnapshot(
        cash=100000.0,
        equity=0.0,
        total_value=100000.0,
        positions=[],
        daily_trades_count=0,
        total_exposure_pct=0.0,
        sector_exposure={},
        max_drawdown_pct=-0.02,
        peak_portfolio_value=100000.0,
    )


async def test_confidence_gate_blocks_low_confidence() -> None:
    agent = DecisionAgent()
    thesis = _thesis(confidence=MIN_CONFIDENCE - 0.1, direction=SignalDirection.BULLISH)
    state = _state(thesis, portfolio=_portfolio())

    result = await agent._execute(state)
    decision = result["decisions"][0]
    assert decision.action.value == "hold"
    assert "confidence_gate" in decision.risk_checks_failed


async def test_position_size_never_exceeds_limits() -> None:
    agent = DecisionAgent()
    thesis = _thesis(confidence=0.99, direction=SignalDirection.BULLISH)
    state = _state(thesis, portfolio=_portfolio())

    result = await agent._execute(state)
    decision = result["decisions"][0]
    if decision.action.value == "buy":
        assert decision.position_size_pct <= MAX_POSITION_PCT
        assert decision.position_size_usd <= MAX_SINGLE_ORDER_USD


async def test_kill_switch_halts_new_entries() -> None:
    agent = DecisionAgent()
    thesis = _thesis(confidence=0.99, direction=SignalDirection.BULLISH)
    portfolio = _portfolio()
    portfolio.max_drawdown_pct = -0.16
    state = _state(thesis, portfolio=portfolio)

    result = await agent._execute(state)
    decision = result["decisions"][0]
    assert decision.action.value == "hold"
    assert "kill_switch" in decision.risk_checks_failed


async def test_correlation_blocks_excess_sector_exposure() -> None:
    agent = DecisionAgent()
    thesis = _thesis(confidence=0.9, direction=SignalDirection.BULLISH, sector="technology")
    portfolio = _portfolio()
    portfolio.positions = [
        PositionSnapshot(
            ticker="MSFT",
            quantity=10,
            avg_entry_price=100,
            current_price=120,
            market_value=1200,
            unrealized_pnl=200,
            unrealized_pnl_pct=0.2,
            peak_price=125,
            holding_duration_hours=12,
            sector="technology",
        ),
        PositionSnapshot(
            ticker="NVDA",
            quantity=5,
            avg_entry_price=100,
            current_price=120,
            market_value=600,
            unrealized_pnl=100,
            unrealized_pnl_pct=0.2,
            peak_price=125,
            holding_duration_hours=12,
            sector="technology",
        ),
        PositionSnapshot(
            ticker="GOOGL",
            quantity=5,
            avg_entry_price=100,
            current_price=120,
            market_value=600,
            unrealized_pnl=100,
            unrealized_pnl_pct=0.2,
            peak_price=125,
            holding_duration_hours=12,
            sector="technology",
        ),
    ]
    state = _state(thesis, portfolio=portfolio)
    result = await agent._execute(state)
    decision = result["decisions"][0]
    assert decision.action.value == "hold"
    assert decision.correlation_check == "too_correlated"
