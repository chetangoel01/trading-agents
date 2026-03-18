"""OpenRouter client with role routing, fallback, and metadata capture."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

import httpx

from config import (
    MODEL_FALLBACKS,
    MODEL_MAP,
    MODEL_MAX_TOKENS,
    MODEL_TEMPERATURE,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    ModelRole,
)
from utils.token_counter import TokenCounter


@dataclass
class LLMCallMetadata:
    model: str
    role: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    estimated_cost_usd: float
    success: bool
    error: str | None = None


class LLMClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=OPENROUTER_BASE_URL,
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            timeout=60.0,
        )
        self._counter = TokenCounter()

    async def close(self) -> None:
        await self._client.aclose()

    async def complete(
        self,
        role: ModelRole,
        messages: list[dict[str, str]],
        *,
        json_mode: bool = False,
        max_tokens: int | None = None,
    ) -> tuple[dict[str, Any], LLMCallMetadata]:
        models = [MODEL_MAP[role], *MODEL_FALLBACKS.get(role, [])]
        last_error: Exception | None = None
        for model in models:
            try:
                return await self._request(
                    role=role,
                    model=model,
                    messages=messages,
                    json_mode=json_mode,
                    max_tokens=max_tokens or MODEL_MAX_TOKENS[model],
                )
            except Exception as exc:
                last_error = exc
                continue
        raise RuntimeError(f"All model attempts failed for role={role}") from last_error

    async def _request(
        self,
        *,
        role: ModelRole,
        model: str,
        messages: list[dict[str, str]],
        json_mode: bool,
        max_tokens: int,
    ) -> tuple[dict[str, Any], LLMCallMetadata]:
        input_text = "\n".join(m.get("content", "") for m in messages)
        input_tokens = self._counter.count(input_text)

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": MODEL_TEMPERATURE[role],
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        start = perf_counter()
        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        body = response.json()
        latency_ms = int((perf_counter() - start) * 1000)

        output_text = ""
        try:
            output_text = body["choices"][0]["message"]["content"]
        except Exception:
            output_text = str(body)
        output_tokens = self._counter.count(output_text)

        # Real pricing should be read from provider metadata when needed.
        estimated_cost_usd = 0.0
        metadata = LLMCallMetadata(
            model=model,
            role=role.value,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            estimated_cost_usd=estimated_cost_usd,
            success=True,
        )
        return body, metadata
