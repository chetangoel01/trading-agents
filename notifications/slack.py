from __future__ import annotations

from typing import Any

import httpx

from config import SLACK_WEBHOOK_URL


def format_slack_message(event: str, payload: dict[str, Any]) -> dict[str, Any]:
    ticker = payload.get("ticker", "n/a")
    return {
        "event": event,
        "text": f"[{event}] ticker={ticker} payload={payload}",
    }


def send_slack_message(event: str, payload: dict[str, Any]) -> dict[str, Any]:
    message = format_slack_message(event, payload)
    if not SLACK_WEBHOOK_URL:
        return {"channel": "slack", "payload": message, "sent": False, "error": "SLACK_WEBHOOK_URL not configured"}
    try:
        resp = httpx.post(SLACK_WEBHOOK_URL, json=message, timeout=10.0)
        resp.raise_for_status()
        return {"channel": "slack", "payload": message, "sent": True}
    except Exception as exc:
        return {"channel": "slack", "payload": message, "sent": False, "error": str(exc)}
