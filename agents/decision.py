from __future__ import annotations

from config import (
    MAX_CORRELATED_POSITIONS,
    MAX_DAILY_TRADES,
    MAX_DRAWDOWN_PCT,
    MAX_POSITION_PCT,
    MAX_SINGLE_ORDER_USD,
    MAX_TOTAL_EXPOSURE_PCT,
    MIN_CONFIDENCE,
    STOP_LOSS_PCT,
    TAKE_PROFIT_PCT,
    TRAILING_STOP_PCT,
)
from agents.base import BaseAgent
from state import ActionType, AgentState, SignalDirection, TradeDecision


class DecisionAgent(BaseAgent):
    name = "decide"

    async def _execute(self, state: AgentState) -> AgentState:
        decisions: list[TradeDecision] = []
        portfolio = state["portfolio"]
        held_tickers = {p.ticker for p in portfolio.positions}

        for thesis in state["theses"]:
            risk_checks_passed: list[str] = []
            risk_checks_failed: list[str] = []
            action = ActionType.HOLD
            correlation_check: str | None = None
            position_size_usd = 0.0
            position_size_pct = 0.0

            if portfolio.max_drawdown_pct <= MAX_DRAWDOWN_PCT:
                risk_checks_failed.append("kill_switch")
            else:
                risk_checks_passed.append("kill_switch")

            if thesis.confidence < MIN_CONFIDENCE:
                risk_checks_failed.append("confidence_gate")
            else:
                risk_checks_passed.append("confidence_gate")

            if portfolio.daily_trades_count >= MAX_DAILY_TRADES:
                risk_checks_failed.append("daily_trade_limit")
            else:
                risk_checks_passed.append("daily_trade_limit")

            if not risk_checks_failed:
                if thesis.direction == SignalDirection.BULLISH and thesis.ticker not in held_tickers:
                    action = ActionType.BUY
                elif thesis.direction == SignalDirection.BEARISH and thesis.ticker in held_tickers:
                    action = ActionType.SELL
                else:
                    action = ActionType.HOLD

            if action == ActionType.BUY:
                same_sector_count = sum(
                    1
                    for p in portfolio.positions
                    if thesis.sector != "unknown" and p.sector == thesis.sector
                )
                if same_sector_count >= MAX_CORRELATED_POSITIONS:
                    action = ActionType.HOLD
                    correlation_check = "too_correlated"
                    risk_checks_failed.append("correlation")
                else:
                    correlation_check = "passed"
                    risk_checks_passed.append("correlation")

            if action == ActionType.BUY:
                raw_position_pct = min(thesis.confidence * MAX_POSITION_PCT, MAX_POSITION_PCT)
                raw_size = raw_position_pct * portfolio.total_value
                capped_size = min(raw_size, MAX_SINGLE_ORDER_USD)
                remaining_exposure_usd = max(
                    0.0,
                    (MAX_TOTAL_EXPOSURE_PCT - portfolio.total_exposure_pct) * portfolio.total_value,
                )
                if remaining_exposure_usd <= 0:
                    action = ActionType.HOLD
                    risk_checks_failed.append("exposure_limit")
                else:
                    capped_size = min(capped_size, remaining_exposure_usd)
                    position_size_usd = capped_size
                    position_size_pct = (
                        capped_size / portfolio.total_value if portfolio.total_value > 0 else 0.0
                    )

            entry_ref_price = 100.0
            stop_loss_price = (
                entry_ref_price * (1 + STOP_LOSS_PCT) if action == ActionType.BUY else None
            )
            take_profit_price = (
                entry_ref_price * (1 + TAKE_PROFIT_PCT) if action == ActionType.BUY else None
            )

            decisions.append(
                TradeDecision(
                    ticker=thesis.ticker,
                    action=action,
                    confidence=thesis.confidence,
                    reasoning=f"direction={thesis.direction.value}",
                    position_size_pct=position_size_pct,
                    position_size_usd=position_size_usd,
                    stop_loss_price=stop_loss_price,
                    take_profit_price=take_profit_price,
                    trailing_stop_pct=TRAILING_STOP_PCT if action == ActionType.BUY else None,
                    strategy_attribution=thesis.dominant_strategy,
                    risk_checks_passed=risk_checks_passed,
                    risk_checks_failed=risk_checks_failed,
                    correlation_check=correlation_check,
                    decision_model="rule_engine_v1",
                    decision_latency_ms=0,
                )
            )

        state["decisions"] = decisions
        return state
