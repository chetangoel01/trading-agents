from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import re

import httpx

from agents.base import BaseAgent
from config import CACHE_TTL_TRANSCRIPTS, FINNHUB_API_KEY, TRANSCRIPT_LOOKBACK_QUARTERS
from state import AgentState, DataSourceType, RawDocument
from utils.cache import Cache


class TranscriptFetcherAgent(BaseAgent):
    name = "fetch_transcripts"

    def __init__(self) -> None:
        super().__init__()
        self.cache = Cache()

    @staticmethod
    def _extract_key_sections(text: str) -> str:
        patterns = [r"ceo remarks", r"cfo remarks", r"q&a", r"q and a"]
        lowered = text.lower()
        starts = [m.start() for p in patterns for m in re.finditer(p, lowered)]
        if not starts:
            return text
        return text[min(starts) :].strip()

    @staticmethod
    def _hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @classmethod
    def _build_doc(cls, ticker: str, title: str, content: str, url: str) -> RawDocument:
        return RawDocument(
            source_type=DataSourceType.EARNINGS_TRANSCRIPT,
            ticker=ticker,
            title=title,
            content=content,
            url=url,
            published_at=None,
            content_hash=cls._hash(content),
            metadata={},
        )

    async def _fetch_transcripts(self, client: httpx.AsyncClient, ticker: str) -> list[RawDocument]:
        if not FINNHUB_API_KEY:
            return []
        cache_key = f"transcript:{ticker}"
        cached = await self.cache.get(cache_key)
        if cached:
            return [RawDocument.model_validate(x) for x in cached]

        params = {"symbol": ticker, "token": FINNHUB_API_KEY}
        response = await client.get("https://finnhub.io/api/v1/stock/transcripts", params=params)
        if response.status_code >= 400:
            return []
        payload = response.json()
        rows = payload.get("transcripts", []) if isinstance(payload, dict) else []
        docs: list[RawDocument] = []
        for row in rows[:TRANSCRIPT_LOOKBACK_QUARTERS]:
            if not isinstance(row, dict):
                continue
            text = row.get("transcript", "")
            if not text:
                continue
            sectioned = self._extract_key_sections(text)
            docs.append(
                self._build_doc(
                    ticker=ticker,
                    title=row.get("title", f"{ticker} earnings transcript"),
                    content=sectioned,
                    url=row.get("url", ""),
                )
            )
        await self.cache.set(
            cache_key,
            [d.model_dump(mode="json") for d in docs],
            ttl=CACHE_TTL_TRANSCRIPTS,
        )
        return docs

    async def _execute(self, state: AgentState) -> AgentState:
        tickers = state["metadata"].tickers
        existing_hashes = {doc.content_hash for doc in state["raw_documents"]}
        async with httpx.AsyncClient(timeout=30.0) as client:
            for ticker in tickers:
                docs = await self._fetch_transcripts(client, ticker)
                if not docs:
                    state["metadata"].warnings.append(
                        {
                            "agent": self.name,
                            "ticker": ticker,
                            "warning": "no transcript data; continuing",
                        }
                    )
                for doc in docs:
                    if doc.content_hash in existing_hashes:
                        continue
                    existing_hashes.add(doc.content_hash)
                    state["raw_documents"].append(doc)
        return state
