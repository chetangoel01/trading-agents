"""OpenRouter client with role routing, fallback, and metadata capture."""

from __future__ import annotations

import re
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


_THINK_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL)
_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)```", re.DOTALL)


def _extract_json(text: str) -> str:
    """Strip thinking tags and markdown fences to isolate JSON content."""
    # Remove <think>...</think> blocks (Qwen3-Coder thinking mode)
    text = _THINK_RE.sub("", text).strip()
    # Extract from markdown code fences if present
    fence_match = _FENCE_RE.search(text)
    if fence_match:
        text = fence_match.group(1).strip()
    return text


class LLMClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=OPENROUTER_BASE_URL,
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            timeout=httpx.Timeout(120.0, connect=10.0),
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
        errors: list[str] = []
        for model in models:
            try:
                return await self._request(
                    role=role,
                    model=model,
                    messages=messages,
                    json_mode=json_mode,
                    max_tokens=max_tokens or MODEL_MAX_TOKENS[model],
                )
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text[:500] if exc.response else str(exc)
                errors.append(f"{model}: HTTP {exc.response.status_code} - {detail}")
            except Exception as exc:
                errors.append(f"{model}: {exc}")
        raise RuntimeError(f"All model attempts failed for role={role}: {'; '.join(errors)}")

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

        if json_mode:
            # Do not use response_format: json_object — it is incompatible with
            # Anthropic models via OpenRouter and with Qwen thinking mode.
            # Instead, enforce JSON output through the system message.
            if messages and messages[0].get("role") == "system":
                messages = [
                    {**messages[0], "content": messages[0]["content"] + "\n\nRespond ONLY with valid JSON. No explanation, no markdown fences."},
                    *messages[1:],
                ]

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": MODEL_TEMPERATURE[role],
            "max_tokens": max_tokens,
        }

        start = perf_counter()
        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        latency_ms = int((perf_counter() - start) * 1000)

        raw = response.text
        if not raw or not raw.strip():
            raise RuntimeError(f"Empty response body from {model} (HTTP {response.status_code})")
        try:
            body = response.json()
        except Exception:
            raise RuntimeError(f"Non-JSON response from {model} (HTTP {response.status_code}): {raw[:300]}")

        output_text = ""
        try:
            output_text = body["choices"][0]["message"]["content"] or ""
        except Exception:
            output_text = str(body)

        # When json_mode is requested, strip thinking tags and markdown fences
        # that models like Qwen3-Coder wrap around JSON output.
        if json_mode and output_text:
            output_text = _extract_json(output_text)
            try:
                body["choices"][0]["message"]["content"] = output_text
            except (KeyError, IndexError):
                pass

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
