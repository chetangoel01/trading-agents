from __future__ import annotations

from agents.base import BaseAgent
from notifications import dispatch_state_notifications
from state import AgentState


class FormatterAgent(BaseAgent):
    name = "format"

    async def _execute(self, state: AgentState) -> AgentState:
        metadata = state["metadata"]
        portfolio = state["portfolio"]
        theses_lines = [
            (
                f"[{thesis.ticker}] {thesis.direction.value} "
                f"(confidence: {thesis.confidence:.2f}) via {thesis.dominant_strategy.value}\n"
                f"  {thesis.summary}"
            )
            for thesis in state["theses"]
        ]
        decision_lines = [
            (
                f"[{decision.ticker}] {decision.action.value} — {decision.reasoning}\n"
                f"  Size: ${decision.position_size_usd:.2f} ({decision.position_size_pct:.2%})\n"
                f"  Risk checks: +{len(decision.risk_checks_passed)} / -{len(decision.risk_checks_failed)}"
            )
            for decision in state["decisions"]
        ]
        order_lines = [
            (
                f"[{order.ticker}] {order.action.value} {order.quantity} @ "
                f"{order.filled_price if order.filled_price is not None else 'n/a'} "
                f"({order.status.value})"
            )
            for order in state["orders"]
        ]
        strategy_perf = state["feedback"].strategy_performance
        feedback_lines = [
            (
                f"[{entry.strategy.value}] trades={entry.total_trades} "
                f"win_rate={entry.win_rate:.2f} avg_pnl={entry.avg_pnl_pct:.2%}"
            )
            for entry in strategy_perf
        ]
        notification_dispatches = dispatch_state_notifications(state)
        notification_events = [item.get("payload", {}).get("event", "unknown") for item in notification_dispatches]

        report = "\n".join(
            [
                "Run Report",
                f"run_id: {metadata.run_id}",
                f"trigger: {metadata.trigger}",
                f"mode: {metadata.run_mode}",
                f"cost_usd: {metadata.total_cost_usd:.4f}",
                "",
                "THESES",
                *(theses_lines or ["(none)"]),
                "",
                "DECISIONS",
                *(decision_lines or ["(none)"]),
                "",
                "ORDERS",
                *(order_lines or ["(none)"]),
                "",
                "PORTFOLIO",
                f"cash: {portfolio.cash:.2f}",
                f"equity: {portfolio.equity:.2f}",
                f"total_value: {portfolio.total_value:.2f}",
                f"daily_trades: {portfolio.daily_trades_count}",
                "",
                "FEEDBACK",
                *(feedback_lines or ["(none)"]),
                "",
                "NOTIFICATIONS",
                *(notification_events or ["(none)"]),
                "",
                f"WARNINGS ({len(metadata.warnings)})",
                *([str(w) for w in metadata.warnings] or ["(none)"]),
                "",
                f"ERRORS ({len(metadata.errors)})",
                *([str(e) for e in metadata.errors] or ["(none)"]),
            ]
        )
        state["formatted_report"] = report
        return state
