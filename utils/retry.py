"""Generic retry utilities with exponential backoff."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


async def retry_async(
    func: Callable[[], Awaitable[T]],
    *,
    retries: int = 3,
    base_delay_seconds: float = 1.0,
    retry_on: tuple[type[Exception], ...] = (Exception,),
) -> T:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            return await func()
        except retry_on as exc:  # type: ignore[misc]
            last_error = exc
            if attempt == retries - 1:
                break
            await asyncio.sleep(base_delay_seconds * (2**attempt))
    assert last_error is not None
    raise last_error
