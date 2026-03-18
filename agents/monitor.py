from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from agents.base import BaseAgent
from config import MAX_DRAWDOWN_PCT, STOP_LOSS_PCT, TAKE_PROFIT_PCT, TRAILING_STOP_PCT
from state import ActionType, AgentState, TradeDecision


class MonitorAgent(BaseAgent):
    name = "monitor"

    def __init__(self, now_provider: Callable[[], datetime] | None = None) -> None:
        super().__init__()
        self._now_provider = now_provider or (lambda: datetime.now(UTC))

    @staticmethod
    def _exit_reason(position) -> str | None:
        if position.unrealized_pnl_pct <= STOP_LOSS_PCT:
            return "stop_loss"
        if position.unrealized_pnl_pct >= TAKE_PROFIT_PCT:
            return "take_profit"
        trailing_floor = position.peak_price * (1 - TRAILING_STOP_PCT)
        if position.current_price <= trailing_floor:
            return "trailing_stop"
        return None

    async def _execute(self, state: AgentState) -> AgentState:
        decisions: list[TradeDecision] = []
        now_utc = self._now_provider()
        portfolio = state["portfolio"]

        for position in portfolio.positions:
            reason = self._exit_reason(position)
            if reason is None:
                continue

            decisions.append(
                TradeDecision(
                    ticker=position.ticker,
                    action=ActionType.SELL,
                    confidence=1.0,
                    reasoning=reason,
                    position_size_pct=0.0,
                    position_size_usd=position.market_value,
                    strategy_attribution=(
                        state["decisions"][0].strategy_attribution
                        if state["decisions"]
                        else "fundamental"
                    ),
                    risk_checks_passed=["monitor_trigger"],
                    risk_checks_failed=[],
                    decision_model="monitor_rule_engine",
                    decision_latency_ms=0,
                )
            )
            portfolio.daily_trades_count += 1
            if reason == "stop_loss":
                portfolio.last_loss_at = now_utc

        if decisions:
            state["decisions"] = decisions

        if portfolio.total_value > 0:
            portfolio.total_exposure_pct = min(
                1.0, sum(p.market_value for p in portfolio.positions) / portfolio.total_value
            )

        if portfolio.peak_portfolio_value > 0:
            drawdown = (portfolio.total_value - portfolio.peak_portfolio_value) / portfolio.peak_portfolio_value
            portfolio.max_drawdown_pct = min(portfolio.max_drawdown_pct, drawdown)
            if drawdown <= MAX_DRAWDOWN_PCT:
                state["metadata"].warnings.append(
                    {"agent": self.name, "warning": "kill switch threshold reached in monitoring"}
                )

        return state
