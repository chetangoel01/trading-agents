from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText
from typing import Any

SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", "trading-agents@localhost")
EMAIL_TO = os.getenv("EMAIL_TO", "")


def format_email_message(event: str, payload: dict[str, Any]) -> dict[str, str]:
    ticker = payload.get("ticker", "n/a")
    return {
        "subject": f"[{event}] {ticker}",
        "body": f"event={event}\npayload={payload}",
    }


def send_email_message(event: str, payload: dict[str, Any]) -> dict[str, Any]:
    email = format_email_message(event, payload)
    if not SMTP_USER or not EMAIL_TO:
        return {"channel": "email", "payload": email, "sent": False, "error": "SMTP not configured"}
    try:
        msg = MIMEText(email["body"])
        msg["Subject"] = email["subject"]
        msg["From"] = EMAIL_FROM
        msg["To"] = EMAIL_TO
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return {"channel": "email", "payload": email, "sent": True}
    except Exception as exc:
        return {"channel": "email", "payload": email, "sent": False, "error": str(exc)}
