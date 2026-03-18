"""Async token-bucket rate limiter."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass


@dataclass
class _Bucket:
    rate: int
    per_seconds: float
    tokens: float
    last_refill: float


class RateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, _Bucket] = {}
        self._lock = asyncio.Lock()

    def add_bucket(self, name: str, *, rate: int, per_seconds: float) -> None:
        now = time.monotonic()
        self._buckets[name] = _Bucket(
            rate=rate,
            per_seconds=per_seconds,
            tokens=float(rate),
            last_refill=now,
        )

    async def acquire(self, name: str) -> None:
        while True:
            async with self._lock:
                bucket = self._buckets[name]
                self._refill(bucket)
                if bucket.tokens >= 1.0:
                    bucket.tokens -= 1.0
                    return
                wait_seconds = max(
                    0.001,
                    (1.0 - bucket.tokens) * (bucket.per_seconds / bucket.rate),
                )
            await asyncio.sleep(wait_seconds)

    @staticmethod
    def _refill(bucket: _Bucket) -> None:
        now = time.monotonic()
        elapsed = now - bucket.last_refill
        refill_amount = elapsed * (bucket.rate / bucket.per_seconds)
        bucket.tokens = min(float(bucket.rate), bucket.tokens + refill_amount)
        bucket.last_refill = now
