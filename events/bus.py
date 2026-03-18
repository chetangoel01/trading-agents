"""Async event bus for inter-component communication."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

EventHandler = Callable[[dict[str, Any]], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        self._handlers[event_name].append(handler)

    async def emit(self, event_name: str, payload: dict[str, Any]) -> None:
        handlers = self._handlers.get(event_name, [])
        if not handlers:
            return
        await asyncio.gather(*(handler(payload) for handler in handlers))
