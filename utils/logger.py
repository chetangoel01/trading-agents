"""Structured JSON logging helpers."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from config import LOG_LEVEL


def _json_formatter(record: logging.LogRecord) -> str:
    payload: dict[str, Any] = {
        "ts": datetime.now(UTC).isoformat(),
        "level": record.levelname,
        "logger": record.name,
        "message": record.getMessage(),
    }
    if hasattr(record, "extra") and isinstance(record.extra, dict):
        payload.update(record.extra)
    return json.dumps(payload, default=str)


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return _json_formatter(record)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger
