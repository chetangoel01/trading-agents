from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from agents.base import BaseAgent
from config import ENABLE_AUTO_WEIGHT_REBALANCE
from state import ActionType, AgentState, OrderStatus, OutcomeResult, StrategyPerformance, StrategyType, TradeOutcome


class FeedbackAgent(BaseAgent):
    name = "feedback"

    @staticmethod
    def _record_outcome_from_order(
        order,
        *,
        entry_price: float = 100.0,
        strategy_attribution: StrategyType = StrategyType.MOMENTUM,
        thesis_confidence: float = 0.8,
        exit_reason: str = "execution",
    ) -> TradeOutcome | None:
        if order.status != OrderStatus.FILLED or order.filled_price is None:
            return None
        now = datetime.now(UTC)
        if entry_price <= 0:
            entry_price = 100.0
        pnl_pct = (order.filled_price - entry_price) / entry_price
        return TradeOutcome(
            ticker=order.ticker,
            action=order.action,
            entry_price=entry_price,
            exit_price=order.filled_price,
            quantity=order.filled_quantity or order.quantity,
            pnl_usd=(order.filled_price - entry_price) * (order.filled_quantity or order.quantity),
            pnl_pct=pnl_pct,
            result=OutcomeResult.WIN if pnl_pct > 0 else OutcomeResult.LOSS,
            holding_duration_hours=1.0,
            strategy_attribution=strategy_attribution,
            thesis_confidence_at_entry=thesis_confidence,
            exit_reason=exit_reason,
            opened_at=now - timedelta(hours=1),
            closed_at=now,
        )

    @staticmethod
    def _compute_calibration(outcomes: list[TradeOutcome]) -> dict[str, float]:
        grouped: dict[str, list[TradeOutcome]] = defaultdict(list)
        for outcome in outcomes:
            grouped[outcome.strategy_attribution.value].append(outcome)

        calibration: dict[str, float] = {}
        for strategy, rows in grouped.items():
            if not rows:
                continue
            avg_conf = sum(r.thesis_confidence_at_entry for r in rows) / len(rows)
            win_rate = sum(1 for r in rows if r.pnl_pct > 0) / len(rows)
            # If confidence persistently exceeds realized win rate, reduce multiplier.
            delta = win_rate - avg_conf
            calibration[strategy] = max(0.5, min(1.5, 1.0 + delta))
        return calibration

    async def _execute(self, state: AgentState) -> AgentState:
        feedback = state["feedback"]

        # Build lookups for real entry prices and strategy attribution
        buy_decisions_by_ticker: dict[str, object] = {}
        for d in state["decisions"]:
            if d.action == ActionType.BUY and d.ticker not in buy_decisions_by_ticker:
                buy_decisions_by_ticker[d.ticker] = d
        positions_by_ticker = {p.ticker: p for p in state["portfolio"].positions}

        new_outcomes: list[TradeOutcome] = []
        for order in state["orders"]:
            if order.action.value != "sell":
                continue
            buy_decision = buy_decisions_by_ticker.get(order.ticker)
            position = positions_by_ticker.get(order.ticker)
            entry_price = (
                position.avg_entry_price if position else
                (buy_decision.entry_price_limit if buy_decision and buy_decision.entry_price_limit else 100.0)
            )
            strategy = buy_decision.strategy_attribution if buy_decision else StrategyType.MOMENTUM
            confidence = buy_decision.confidence if buy_decision else 0.8
            exit_reason = getattr(order, "rejected_reason", None) or "execution"
            outcome = self._record_outcome_from_order(
                order,
                entry_price=entry_price,
                strategy_attribution=strategy,
                thesis_confidence=confidence,
                exit_reason=exit_reason,
            )
            if outcome is not None:
                new_outcomes.append(outcome)

        if new_outcomes:
            feedback.outcomes.extend(new_outcomes)

        feedback.confidence_calibration = self._compute_calibration(feedback.outcomes)

        # Lightweight rolling performance summary by strategy.
        per_strategy: dict[str, list[TradeOutcome]] = defaultdict(list)
        for outcome in feedback.outcomes:
            per_strategy[outcome.strategy_attribution.value].append(outcome)

        now = datetime.now(UTC)
        perf_rows: list[StrategyPerformance] = []
        for strategy, rows in per_strategy.items():
            pnl_values = [r.pnl_pct for r in rows]
            max_drawdown = min(pnl_values) if pnl_values else 0.0
            win_rate = sum(1 for r in rows if r.pnl_pct > 0) / len(rows)
            perf_rows.append(
                StrategyPerformance(
                    strategy=StrategyType(strategy),
                    total_trades=len(rows),
                    win_rate=win_rate,
                    avg_pnl_pct=sum(pnl_values) / len(pnl_values),
                    max_drawdown_pct=max_drawdown,
                    recommended_weight_adjustment=0.0,
                    period_start=min(r.opened_at for r in rows),
                    period_end=max(r.closed_at for r in rows),
                )
            )
        feedback.strategy_performance = perf_rows

        if ENABLE_AUTO_WEIGHT_REBALANCE:
            feedback.last_rebalance_at = now

        return state
