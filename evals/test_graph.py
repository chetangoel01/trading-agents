from __future__ import annotations

from datetime import UTC, datetime

from graph import route_after_decision
from state import (
    ActionType,
    AgentState,
    FeedbackState,
    PortfolioSnapshot,
    RunMetadata,
    StrategyType,
    TradeDecision,
)


def _base_state() -> AgentState:
    return AgentState(
        metadata=RunMetadata(
            run_id="run-1",
            started_at=datetime.now(UTC),
            tickers=["AAPL"],
            trigger="manual",
            run_mode="single",
        ),
        raw_documents=[],
        technical_data=[],
        extracted_signals=[],
        strategy_signals=[],
        theses=[],
        decisions=[],
        orders=[],
        portfolio=PortfolioSnapshot(),
        feedback=FeedbackState(),
        formatted_report=None,
    )


def test_route_after_decision_executes_when_actionable() -> None:
    state = _base_state()
    state["decisions"] = [
        TradeDecision(
            ticker="AAPL",
            action=ActionType.BUY,
            confidence=0.9,
            reasoning="bullish signal",
            position_size_pct=0.1,
            position_size_usd=1000,
            strategy_attribution=StrategyType.FUNDAMENTAL,
            decision_model="test",
            decision_latency_ms=10,
        )
    ]
    assert route_after_decision(state) == "execute"


def test_route_after_decision_skips_when_all_hold() -> None:
    state = _base_state()
    state["decisions"] = [
        TradeDecision(
            ticker="AAPL",
            action=ActionType.HOLD,
            confidence=0.2,
            reasoning="no edge",
            position_size_pct=0.0,
            position_size_usd=0.0,
            strategy_attribution=StrategyType.FUNDAMENTAL,
            decision_model="test",
            decision_latency_ms=10,
        )
    ]
    assert route_after_decision(state) == "skip_to_feedback"
