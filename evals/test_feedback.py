from __future__ import annotations

from datetime import UTC, datetime

from agents.feedback import FeedbackAgent
from state import (
    ActionType,
    AgentState,
    FeedbackState,
    OrderRecord,
    OrderStatus,
    PortfolioSnapshot,
    RunMetadata,
    StrategyType,
    TradeOutcome,
)


def _state(orders: list[OrderRecord], feedback: FeedbackState | None = None) -> AgentState:
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
        orders=orders,
        portfolio=PortfolioSnapshot(
            cash=100000.0,
            equity=0.0,
            total_value=100000.0,
            peak_portfolio_value=100000.0,
        ),
        feedback=feedback or FeedbackState(),
        formatted_report=None,
    )


def _sell_order(*, fill_price: float = 95.0) -> OrderRecord:
    return OrderRecord(
        ticker="AAPL",
        action=ActionType.SELL,
        quantity=10,
        order_type="market",
        status=OrderStatus.FILLED,
        filled_price=fill_price,
        filled_quantity=10,
    )


def _loss_outcome() -> TradeOutcome:
    now = datetime.now(UTC)
    return TradeOutcome(
        ticker="AAPL",
        action=ActionType.SELL,
        entry_price=100.0,
        exit_price=95.0,
        quantity=10,
        pnl_usd=-50.0,
        pnl_pct=-0.05,
        result="loss",
        holding_duration_hours=6.0,
        strategy_attribution=StrategyType.MOMENTUM,
        thesis_confidence_at_entry=0.9,
        exit_reason="stop_loss",
        opened_at=now,
        closed_at=now,
    )


async def test_feedback_records_outcome_for_filled_sell() -> None:
    agent = FeedbackAgent()
    state = _state([_sell_order()])
    result = await agent._execute(state)
    assert len(result["feedback"].outcomes) == 1
    assert result["feedback"].outcomes[0].ticker == "AAPL"


async def test_feedback_calibration_reduces_for_overconfident_losses() -> None:
    agent = FeedbackAgent()
    fb = FeedbackState(outcomes=[_loss_outcome(), _loss_outcome(), _loss_outcome()])
    state = _state([], feedback=fb)
    result = await agent._execute(state)
    momentum_calibration = result["feedback"].confidence_calibration.get("momentum")
    assert momentum_calibration is not None
    assert momentum_calibration < 1.0
