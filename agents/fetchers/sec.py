from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import re
from typing import Any

import httpx

from agents.base import BaseAgent
from config import (
    CACHE_TTL_SEC_FILINGS,
    SEC_BASE_URL,
    SEC_FILING_TYPES,
    SEC_LOOKBACK_DAYS,
    SEC_MAX_FILINGS_PER_TICKER,
    SEC_REQUESTS_PER_SECOND,
    SEC_USER_AGENT,
)
from state import AgentState, DataSourceType, FilingType, RawDocument
from utils.cache import Cache
from utils.rate_limiter import RateLimiter


class SECFetcherAgent(BaseAgent):
    name = "fetch_sec"

    def __init__(self) -> None:
        super().__init__()
        self.cache = Cache()
        self.limiter = RateLimiter()
        self.limiter.add_bucket("sec", rate=SEC_REQUESTS_PER_SECOND, per_seconds=1)

    @staticmethod
    def _hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _parse_filing_type(value: str | None) -> FilingType | None:
        if value == "10-K":
            return FilingType.TEN_K
        if value == "10-Q":
            return FilingType.TEN_Q
        if value == "8-K":
            return FilingType.EIGHT_K
        return None

    @staticmethod
    def _extract_relevant_sections(text: str, filing_type: str | None) -> str:
        # Keep extraction deterministic and transparent for testability.
        filing_type = filing_type or ""
        if filing_type == "8-K":
            return text

        if filing_type == "10-K":
            patterns = [r"item\s+1a", r"item\s+7", r"item\s+8"]
        elif filing_type == "10-Q":
            patterns = [r"item\s+1", r"item\s+2"]
        else:
            return text

        lowered = text.lower()
        starts = [m.start() for p in patterns for m in re.finditer(p, lowered)]
        if not starts:
            return text
        start = min(starts)
        return text[start:]

    @classmethod
    def _build_raw_document(
        cls,
        *,
        ticker: str,
        title: str,
        content: str,
        url: str,
        filing_type: str | None,
        published_at: datetime | None = None,
        truncated: bool = False,
    ) -> RawDocument:
        parsed_filing_type = cls._parse_filing_type(filing_type)
        return RawDocument(
            source_type=DataSourceType.SEC_FILING,
            ticker=ticker,
            title=title,
            content=content,
            url=url,
            published_at=published_at,
            filing_type=parsed_filing_type,
            content_hash=cls._hash(content),
            truncated=truncated,
            metadata={},
        )

    @staticmethod
    def _select_filing_entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
        hits = payload.get("hits") or payload.get("filings") or []
        if not isinstance(hits, list):
            return []
        return [h for h in hits if isinstance(h, dict)]

    async def _execute(self, state: AgentState) -> AgentState:
        tickers = state["metadata"].tickers
        if not SEC_USER_AGENT:
            state["metadata"].warnings.append(
                {"agent": self.name, "warning": "SEC_USER_AGENT missing; skipping SEC fetch"}
            )
            return state

        async with httpx.AsyncClient(
            timeout=30.0, headers={"User-Agent": SEC_USER_AGENT}
        ) as client:
            for ticker in tickers:
                await self.limiter.acquire("sec")
                try:
                    state = await self._fetch_for_ticker(state, client, ticker)
                except Exception as exc:
                    state["metadata"].warnings.append(
                        {"agent": self.name, "ticker": ticker, "warning": str(exc)}
                    )
        return state

    async def _fetch_for_ticker(
        self, state: AgentState, client: httpx.AsyncClient, ticker: str
    ) -> AgentState:
        start_dt = (datetime.now(UTC) - timedelta(days=SEC_LOOKBACK_DAYS)).date().isoformat()
        end_dt = datetime.now(UTC).date().isoformat()

        params = {
            "q": f'"{ticker}"',
            "dateRange": "custom",
            "startdt": start_dt,
            "enddt": end_dt,
            "forms": ",".join(SEC_FILING_TYPES),
        }
        response = await client.get(SEC_BASE_URL, params=params)
        response.raise_for_status()
        entries = self._select_filing_entries(response.json())[:SEC_MAX_FILINGS_PER_TICKER]

        existing_hashes = {doc.content_hash for doc in state["raw_documents"]}
        for entry in entries:
            filing_url = entry.get("link") or entry.get("url")
            if not filing_url:
                continue
            filing_type = entry.get("form") or entry.get("filingType")
            cache_key = f"sec:{ticker}:{filing_type}:{filing_url}"
            cached = await self.cache.get(cache_key)
            if cached:
                doc = RawDocument.model_validate(cached)
            else:
                filing_response = await client.get(filing_url)
                filing_response.raise_for_status()
                section_text = self._extract_relevant_sections(filing_response.text, filing_type)
                if not section_text.strip():
                    continue
                doc = self._build_raw_document(
                    ticker=ticker,
                    title=entry.get("title", f"{ticker} {filing_type or 'filing'}"),
                    content=section_text,
                    url=filing_url,
                    filing_type=filing_type,
                    published_at=None,
                )
                await self.cache.set(
                    cache_key,
                    doc.model_dump(mode="json"),
                    ttl=CACHE_TTL_SEC_FILINGS,
                )

            if doc.content_hash in existing_hashes:
                continue
            existing_hashes.add(doc.content_hash)
            state["raw_documents"].append(doc)
        return state
