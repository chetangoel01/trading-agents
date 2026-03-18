"""Redis-backed cache with in-memory fallback."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from config import REDIS_OPTIONAL, REDIS_URL

try:
    import redis.asyncio as redis
except Exception:  # pragma: no cover - dependency/environment specific
    redis = None


class Cache:
    def __init__(self, redis_url: str = REDIS_URL) -> None:
        self._memory: dict[str, tuple[datetime, str]] = {}
        self._redis_client = None
        if redis is not None:
            try:
                self._redis_client = redis.from_url(redis_url, decode_responses=True)
            except Exception:
                if not REDIS_OPTIONAL:
                    raise

    async def get(self, key: str) -> Any | None:
        if self._redis_client is not None:
            try:
                value = await self._redis_client.get(key)
                if value is not None:
                    return json.loads(value)
            except Exception:
                # Graceful fallback to memory cache.
                pass

        memory_value = self._memory.get(key)
        if memory_value is None:
            return None
        expires_at, payload = memory_value
        if datetime.now(UTC) >= expires_at:
            self._memory.pop(key, None)
            return None
        return json.loads(payload)

    async def set(self, key: str, value: Any, ttl: int) -> None:
        serialized = json.dumps(value, default=str)
        if self._redis_client is not None:
            try:
                await self._redis_client.set(key, serialized, ex=ttl)
                return
            except Exception:
                pass
        self._memory[key] = (datetime.now(UTC) + timedelta(seconds=ttl), serialized)

    async def invalidate(self, prefix: str) -> int:
        removed = 0
        memory_keys = [k for k in self._memory if k.startswith(prefix)]
        for key in memory_keys:
            self._memory.pop(key, None)
            removed += 1

        if self._redis_client is not None:
            try:
                cursor = "0"
                while True:
                    cursor, keys = await self._redis_client.scan(cursor=cursor, match=f"{prefix}*")
                    if keys:
                        removed += len(keys)
                        await self._redis_client.delete(*keys)
                    if cursor == 0 or cursor == "0":
                        break
            except Exception:
                pass
        return removed
