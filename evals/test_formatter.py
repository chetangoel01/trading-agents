from __future__ import annotations

from datetime import UTC, datetime

from agents.formatter import FormatterAgent
from state import (
    ActionType,
    AgentState,
    FeedbackState,
    OrderRecord,
    OrderStatus,
    PortfolioSnapshot,
    RunMetadata,
    SignalDirection,
    StrategyType,
    TickerThesis,
    TradeDecision,
)


def _state() -> AgentState:
    metadata = RunMetadata(
        run_id="run-report-1",
        started_at=datetime.now(UTC),
        tickers=["AAPL"],
        trigger="manual",
        run_mode="single",
        warnings=[{"message": "sample warning"}],
        errors=[],
        total_cost_usd=0.12,
    )
    thesis = TickerThesis(
        ticker="AAPL",
        direction=SignalDirection.BULLISH,
        confidence=0.72,
        summary="Revenue growth remains resilient.",
        bull_case="AI demand supports margins.",
        bear_case="Macro slowdown pressures multiples.",
        key_catalysts=["earnings beat"],
        key_risks=["valuation risk"],
        strategy_signals=[],
        dominant_strategy=StrategyType.FUNDAMENTAL,
        data_freshness_hours=3.0,
        signal_count=4,
        conflicting_signals=1,
        sector="technology",
        synthesis_model="claude",
        synthesis_latency_ms=120,
    )
    decision = TradeDecision(
        ticker="AAPL",
        action=ActionType.BUY,
        confidence=0.72,
        reasoning="Bullish thesis with acceptable risk.",
        position_size_pct=0.02,
        position_size_usd=2000.0,
        stop_loss_price=95.0,
        take_profit_price=110.0,
        trailing_stop_pct=0.05,
        strategy_attribution=StrategyType.FUNDAMENTAL,
        risk_checks_passed=["confidence_gate", "daily_trade_limit"],
        risk_checks_failed=[],
        correlation_check="passed",
        decision_model="rule_engine_v1",
        decision_latency_ms=5,
    )
    order = OrderRecord(
        ticker="AAPL",
        action=ActionType.BUY,
        quantity=20,
        order_type="market",
        status=OrderStatus.FILLED,
        filled_price=100.0,
        filled_quantity=20,
    )
    portfolio = PortfolioSnapshot(
        cash=98000.0,
        equity=2000.0,
        total_value=100000.0,
        daily_trades_count=1,
        total_exposure_pct=0.02,
        sector_exposure={"technology": 0.02},
        max_drawdown_pct=0.01,
        peak_portfolio_value=101000.0,
    )
    return AgentState(
        metadata=metadata,
        raw_documents=[],
        technical_data=[],
        extracted_signals=[],
        strategy_signals=[],
        theses=[thesis],
        decisions=[decision],
        orders=[order],
        portfolio=portfolio,
        feedback=FeedbackState(),
        formatted_report=None,
    )


async def test_formatter_generates_non_empty_report_with_required_sections() -> None:
    agent = FormatterAgent()
    state = _state()
    result = await agent._execute(state)
    report = result["formatted_report"]
    assert report is not None
    assert report.strip() != ""
    assert "Run Report" in report
    assert "THESES" in report
    assert "DECISIONS" in report
    assert "ORDERS" in report
    assert "PORTFOLIO" in report
    assert "FEEDBACK" in report
    assert "NOTIFICATIONS" in report
    assert "WARNINGS (1)" in report


async def test_formatter_includes_notification_events_for_orders_and_errors() -> None:
    agent = FormatterAgent()
    state = _state()
    state["metadata"].warnings = [{"warning": "kill switch threshold reached in monitoring"}]
    state["metadata"].errors = [{"agent": "extract", "error": "boom"}]
    result = await agent._execute(state)
    report = result["formatted_report"] or ""
    assert "order_filled" in report
    assert "kill_switch_warning" in report
    assert "pipeline_error_critical" in report
