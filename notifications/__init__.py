from __future__ import annotations

from typing import Any

from notifications.email import send_email_message
from notifications.slack import send_slack_message


_ROUTING: dict[str, list[str]] = {
    "order_filled": ["slack"],
    "stop_loss_triggered": ["slack", "email"],
    "kill_switch_warning": ["slack", "email"],
    "pipeline_error_critical": ["slack"],
}


def route_notification(event: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    channels = _ROUTING.get(event, [])
    dispatched: list[dict[str, Any]] = []
    for channel in channels:
        if channel == "slack":
            dispatched.append(send_slack_message(event, payload))
        elif channel == "email":
            dispatched.append(send_email_message(event, payload))
    return dispatched


def dispatch_state_notifications(state: dict[str, Any]) -> list[dict[str, Any]]:
    dispatched: list[dict[str, Any]] = []
    orders = state.get("orders", [])
    metadata = state.get("metadata")

    for order in orders:
        status = getattr(order, "status", None)
        status_value = getattr(status, "value", str(status)) if status is not None else ""
        if status_value == "filled":
            payload = {
                "ticker": getattr(order, "ticker", "n/a"),
                "action": getattr(getattr(order, "action", None), "value", "n/a"),
                "quantity": getattr(order, "quantity", 0),
                "filled_price": getattr(order, "filled_price", None),
            }
            dispatched.extend(route_notification("order_filled", payload))

    decisions = state.get("decisions", [])
    for decision in decisions:
        action_value = getattr(getattr(decision, "action", None), "value", "")
        reasoning = getattr(decision, "reasoning", "")
        if action_value == "sell" and reasoning in ("stop_loss", "trailing_stop", "take_profit"):
            payload = {
                "event": "stop_loss_triggered",
                "ticker": getattr(decision, "ticker", "n/a"),
                "reason": reasoning,
            }
            dispatched.extend(route_notification("stop_loss_triggered", payload))

    if metadata is not None:
        warnings = getattr(metadata, "warnings", [])
        errors = getattr(metadata, "errors", [])
        for warning in warnings:
            warning_text = str(warning).lower()
            if "kill switch" in warning_text:
                dispatched.extend(route_notification("kill_switch_warning", {"warning": warning}))
                break
        if errors:
            dispatched.extend(route_notification("pipeline_error_critical", {"errors": errors}))

    return dispatched
