from __future__ import annotations

from datetime import UTC, datetime

from agents.execution import ExecutionAgent
from state import (
    ActionType,
    AgentState,
    FeedbackState,
    OrderStatus,
    PortfolioSnapshot,
    PositionSnapshot,
    RunMetadata,
    StrategyType,
    TradeDecision,
)


def _state(
    decisions: list[TradeDecision],
    *,
    execution_enabled: bool = True,
    now_utc: datetime | None = None,
) -> AgentState:
    return AgentState(
        metadata=RunMetadata(
            run_id="run-1",
            started_at=datetime.now(UTC),
            tickers=["AAPL"],
            trigger="manual",
            run_mode="single",
            execution_enabled=execution_enabled,
        ),
        raw_documents=[],
        technical_data=[],
        extracted_signals=[],
        strategy_signals=[],
        theses=[],
        decisions=decisions,
        orders=[],
        portfolio=PortfolioSnapshot(
            cash=100000.0,
            equity=0.0,
            total_value=100000.0,
            positions=[
                PositionSnapshot(
                    ticker="AAPL",
                    quantity=10,
                    avg_entry_price=100.0,
                    current_price=110.0,
                    market_value=1100.0,
                    unrealized_pnl=100.0,
                    unrealized_pnl_pct=0.1,
                    peak_price=112.0,
                    holding_duration_hours=4.0,
                    sector="technology",
                )
            ],
            daily_trades_count=0,
            total_exposure_pct=0.1,
            sector_exposure={"technology": 0.1},
            max_drawdown_pct=-0.02,
            peak_portfolio_value=100000.0,
        ),
        feedback=FeedbackState(),
        formatted_report=None,
    )


def _buy_decision() -> TradeDecision:
    return TradeDecision(
        ticker="AAPL",
        action=ActionType.BUY,
        confidence=0.9,
        reasoning="buy",
        position_size_pct=0.05,
        position_size_usd=5000.0,
        stop_loss_price=95.0,
        take_profit_price=115.0,
        trailing_stop_pct=0.03,
        strategy_attribution=StrategyType.FUNDAMENTAL,
        decision_model="test",
        decision_latency_ms=1,
    )


def _sell_decision() -> TradeDecision:
    return TradeDecision(
        ticker="AAPL",
        action=ActionType.SELL,
        confidence=0.9,
        reasoning="sell",
        position_size_pct=0.0,
        position_size_usd=0.0,
        strategy_attribution=StrategyType.FUNDAMENTAL,
        decision_model="test",
        decision_latency_ms=1,
    )


async def test_execution_skips_when_run_window_disables_execution() -> None:
    agent = ExecutionAgent(now_provider=lambda: datetime(2026, 3, 18, 15, 0, tzinfo=UTC))
    state = _state([_buy_decision()], execution_enabled=False)
    result = await agent._execute(state)
    assert result["orders"] == []
    assert any("execution disabled" in w["warning"] for w in result["metadata"].warnings)


async def test_execution_drops_orders_when_market_closed() -> None:
    # 8:00 ET -> market closed
    agent = ExecutionAgent(now_provider=lambda: datetime(2026, 3, 18, 12, 0, tzinfo=UTC))
    state = _state([_buy_decision()], execution_enabled=True)
    result = await agent._execute(state)
    assert result["orders"] == []
    assert any("market closed" in w["warning"] for w in result["metadata"].warnings)


async def test_execution_creates_market_order_with_bracket_fields() -> None:
    # 10:00 ET -> market open
    agent = ExecutionAgent(now_provider=lambda: datetime(2026, 3, 18, 14, 0, tzinfo=UTC))
    state = _state([_buy_decision()], execution_enabled=True)
    result = await agent._execute(state)
    assert len(result["orders"]) == 1
    order = result["orders"][0]
    assert order.order_type == "market"
    assert order.status == OrderStatus.FILLED
    assert order.stop_price == 95.0
    assert order.limit_price == 115.0


async def test_partial_fill_logs_cancelled_remainder() -> None:
    agent = ExecutionAgent(now_provider=lambda: datetime(2026, 3, 18, 14, 0, tzinfo=UTC))
    decision = _buy_decision()
    primary, remainder = agent._simulate_order_records(decision, quantity=10, fill_ratio=0.4)
    assert primary.status == OrderStatus.PARTIALLY_FILLED
    assert primary.filled_quantity == 4
    assert remainder is not None
    assert remainder.status == OrderStatus.CANCELLED
    assert remainder.quantity == 6


async def test_sell_uses_existing_position_quantity() -> None:
    agent = ExecutionAgent(now_provider=lambda: datetime(2026, 3, 18, 14, 0, tzinfo=UTC))
    state = _state([_sell_decision()], execution_enabled=True)
    result = await agent._execute(state)
    assert len(result["orders"]) == 1
    assert result["orders"][0].quantity == 10
