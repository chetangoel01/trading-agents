from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from math import floor
from zoneinfo import ZoneInfo

from agents.base import BaseAgent
from config import CANONICAL_TZ, DROP_DECISIONS_WHEN_MARKET_CLOSED, MARKET_HOURS_ONLY
from state import ActionType, AgentState, OrderRecord, OrderStatus, TradeDecision


class ExecutionAgent(BaseAgent):
    name = "execute"

    def __init__(self, now_provider: Callable[[], datetime] | None = None) -> None:
        super().__init__()
        self._now_provider = now_provider or (lambda: datetime.now(UTC))

    @staticmethod
    def _is_market_open(now_utc: datetime) -> bool:
        local_dt = now_utc.astimezone(ZoneInfo(CANONICAL_TZ))
        if local_dt.weekday() >= 5:  # Sat/Sun
            return False
        minutes = local_dt.hour * 60 + local_dt.minute
        return (9 * 60 + 30) <= minutes < (16 * 60)

    @staticmethod
    def _position_qty(state: AgentState, ticker: str) -> int:
        for position in state["portfolio"].positions:
            if position.ticker == ticker:
                return position.quantity
        return 0

    @staticmethod
    def _buy_quantity(decision: TradeDecision) -> int:
        price = decision.entry_price_limit or 100.0
        if price <= 0:
            return 0
        return max(0, floor(decision.position_size_usd / price))

    def _simulate_order_records(
        self, decision: TradeDecision, *, quantity: int, fill_ratio: float = 1.0
    ) -> tuple[OrderRecord, OrderRecord | None]:
        now_utc = self._now_provider()
        fill_qty = int(quantity * fill_ratio)
        if fill_qty < 0:
            fill_qty = 0
        if fill_qty > quantity:
            fill_qty = quantity
        remaining = quantity - fill_qty

        if fill_qty == quantity:
            status = OrderStatus.FILLED
        elif fill_qty > 0:
            status = OrderStatus.PARTIALLY_FILLED
        else:
            status = OrderStatus.REJECTED

        primary = OrderRecord(
            ticker=decision.ticker,
            action=decision.action,
            quantity=quantity,
            order_type="market",
            limit_price=decision.take_profit_price,
            stop_price=decision.stop_loss_price,
            trailing_pct=decision.trailing_stop_pct,
            status=status,
            filled_price=decision.entry_price_limit or 100.0,
            filled_quantity=fill_qty if fill_qty > 0 else None,
            filled_at=now_utc if fill_qty > 0 else None,
            rejected_reason="no_fill" if fill_qty == 0 else None,
        )

        remainder_order: OrderRecord | None = None
        if remaining > 0 and fill_qty > 0:
            remainder_order = OrderRecord(
                ticker=decision.ticker,
                action=decision.action,
                quantity=remaining,
                order_type="market",
                status=OrderStatus.CANCELLED,
                rejected_reason="cancelled_unfilled_remainder",
            )
        return primary, remainder_order

    async def _execute(self, state: AgentState) -> AgentState:
        if not state["metadata"].execution_enabled:
            state["metadata"].warnings.append(
                {"agent": self.name, "warning": "execution disabled for this run window"}
            )
            return state

        now_utc = self._now_provider()
        if MARKET_HOURS_ONLY and not self._is_market_open(now_utc):
            if DROP_DECISIONS_WHEN_MARKET_CLOSED:
                state["metadata"].warnings.append(
                    {"agent": self.name, "warning": "market closed; dropping actionable decisions"}
                )
                return state

        orders: list[OrderRecord] = []
        for decision in state["decisions"]:
            if decision.action == ActionType.HOLD:
                continue

            if decision.action in {ActionType.BUY, ActionType.SCALE_IN}:
                qty = self._buy_quantity(decision)
            elif decision.action in {ActionType.SELL, ActionType.SCALE_OUT}:
                qty = self._position_qty(state, decision.ticker)
            else:
                qty = 0

            if qty <= 0:
                state["metadata"].warnings.append(
                    {
                        "agent": self.name,
                        "ticker": decision.ticker,
                        "warning": "non-positive order quantity; skipping",
                    }
                )
                continue

            primary, remainder = self._simulate_order_records(decision, quantity=qty, fill_ratio=1.0)
            orders.append(primary)
            if remainder is not None:
                orders.append(remainder)

        state["orders"].extend(orders)
        return state
