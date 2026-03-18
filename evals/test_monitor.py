from __future__ import annotations

from datetime import UTC, datetime, timedelta

from agents.monitor import MonitorAgent
from config import STOP_LOSS_PCT, TAKE_PROFIT_PCT, TRAILING_STOP_PCT
from state import (
    ActionType,
    AgentState,
    FeedbackState,
    PortfolioSnapshot,
    PositionSnapshot,
    RunMetadata,
)


def _state(position: PositionSnapshot) -> AgentState:
    return AgentState(
        metadata=RunMetadata(
            run_id="run-1",
            started_at=datetime.now(UTC),
            tickers=[position.ticker],
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
        portfolio=PortfolioSnapshot(
            cash=20000.0,
            equity=position.market_value,
            total_value=20000.0 + position.market_value,
            positions=[position],
            daily_trades_count=0,
            total_exposure_pct=0.2,
            sector_exposure={position.sector: 0.2},
            max_drawdown_pct=-0.02,
            peak_portfolio_value=25000.0,
        ),
        feedback=FeedbackState(),
        formatted_report=None,
    )


def _position(*, pnl_pct: float, peak_price: float, current_price: float) -> PositionSnapshot:
    return PositionSnapshot(
        ticker="AAPL",
        quantity=10,
        avg_entry_price=100.0,
        current_price=current_price,
        market_value=current_price * 10,
        unrealized_pnl=(current_price - 100.0) * 10,
        unrealized_pnl_pct=pnl_pct,
        peak_price=peak_price,
        stop_loss_price=95.0,
        take_profit_price=115.0,
        trailing_stop_price=peak_price * (1 - TRAILING_STOP_PCT),
        holding_duration_hours=4.0,
        sector="technology",
    )


async def test_monitor_triggers_stop_loss_exit() -> None:
    agent = MonitorAgent()
    state = _state(_position(pnl_pct=STOP_LOSS_PCT - 0.01, peak_price=103.0, current_price=93.0))
    result = await agent._execute(state)
    assert len(result["decisions"]) == 1
    assert result["decisions"][0].action == ActionType.SELL
    assert result["decisions"][0].reasoning == "stop_loss"


async def test_monitor_triggers_take_profit_exit() -> None:
    agent = MonitorAgent()
    state = _state(_position(pnl_pct=TAKE_PROFIT_PCT + 0.01, peak_price=120.0, current_price=116.0))
    result = await agent._execute(state)
    assert len(result["decisions"]) == 1
    assert result["decisions"][0].action == ActionType.SELL
    assert result["decisions"][0].reasoning == "take_profit"


async def test_monitor_triggers_trailing_stop_exit() -> None:
    agent = MonitorAgent()
    peak_price = 120.0
    current_price = peak_price * (1 - TRAILING_STOP_PCT) - 0.5
    state = _state(_position(pnl_pct=0.08, peak_price=peak_price, current_price=current_price))
    result = await agent._execute(state)
    assert len(result["decisions"]) == 1
    assert result["decisions"][0].action == ActionType.SELL
    assert result["decisions"][0].reasoning == "trailing_stop"


async def test_monitor_updates_last_loss_at_on_stop_trigger() -> None:
    agent = MonitorAgent(now_provider=lambda: datetime(2026, 3, 18, 14, 0, tzinfo=UTC))
    state = _state(_position(pnl_pct=STOP_LOSS_PCT - 0.01, peak_price=104.0, current_price=93.0))
    result = await agent._execute(state)
    assert result["portfolio"].last_loss_at == datetime(2026, 3, 18, 14, 0, tzinfo=UTC)
    assert result["portfolio"].daily_trades_count == 1


async def test_monitor_no_exit_when_thresholds_not_hit() -> None:
    agent = MonitorAgent()
    state = _state(_position(pnl_pct=0.01, peak_price=110.0, current_price=109.0))
    result = await agent._execute(state)
    assert result["decisions"] == []
