from __future__ import annotations

from notifications import route_notification
from notifications.email import format_email_message
from notifications.slack import format_slack_message


def test_slack_payload_formatting_for_order_fill() -> None:
    message = format_slack_message(
        "order_filled",
        {"ticker": "AAPL", "action": "buy", "quantity": 10, "filled_price": 198.5},
    )
    assert "AAPL" in message["text"]
    assert "order_filled" in message["event"]


def test_email_payload_formatting_for_stop_loss() -> None:
    email = format_email_message(
        "stop_loss_triggered",
        {"ticker": "MSFT", "price": 390.2},
    )
    assert "MSFT" in email["subject"]
    assert "stop_loss_triggered" in email["body"]


def test_notification_routing_stop_loss_sends_slack_and_email() -> None:
    dispatched = route_notification(
        "stop_loss_triggered",
        {"ticker": "NVDA", "price": 820.0},
    )
    channels = {item["channel"] for item in dispatched}
    assert channels == {"slack", "email"}


def test_notification_routing_order_fill_sends_slack_only() -> None:
    dispatched = route_notification(
        "order_filled",
        {"ticker": "AAPL", "filled_price": 198.5},
    )
    channels = [item["channel"] for item in dispatched]
    assert channels == ["slack"]
