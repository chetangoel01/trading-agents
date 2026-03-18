from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
from typing import Any

import feedparser
import httpx

from agents.base import BaseAgent
from config import (
    CACHE_TTL_NEWS,
    FINNHUB_API_KEY,
    NEWS_LOOKBACK_HOURS,
    NEWS_MAX_ARTICLES_PER_TICKER,
    NEWS_RSS_FEEDS,
)
from state import AgentState, DataSourceType, RawDocument
from utils.cache import Cache


class NewsFetcherAgent(BaseAgent):
    name = "fetch_news"

    def __init__(self) -> None:
        super().__init__()
        self.cache = Cache()

    @staticmethod
    def _hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @classmethod
    def _build_doc(
        cls,
        *,
        ticker: str,
        title: str,
        content: str,
        url: str,
        source_name: str,
    ) -> RawDocument:
        return RawDocument(
            source_type=DataSourceType.NEWS_ARTICLE,
            ticker=ticker,
            title=title,
            content=content,
            url=url,
            published_at=None,
            content_hash=cls._hash(content),
            metadata={"source": source_name},
        )

    @staticmethod
    def _mentions_ticker(text: str, ticker: str) -> bool:
        upper = text.upper()
        t = ticker.upper()
        return f" {t} " in f" {upper} " or f"${t}" in upper

    def _rss_docs(self, ticker: str, feed_url: str) -> list[RawDocument]:
        parsed = feedparser.parse(feed_url)
        docs: list[RawDocument] = []
        for entry in parsed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            body = f"{title}\n{summary}".strip()
            if not body or not self._mentions_ticker(body, ticker):
                continue
            link = entry.get("link", feed_url)
            docs.append(
                self._build_doc(
                    ticker=ticker,
                    title=title or f"{ticker} news",
                    content=body,
                    url=link,
                    source_name="rss",
                )
            )
        return docs

    async def _execute(self, state: AgentState) -> AgentState:
        tickers = state["metadata"].tickers
        existing_hashes = {doc.content_hash for doc in state["raw_documents"]}
        async with httpx.AsyncClient(timeout=30.0) as client:
            for ticker in tickers:
                for doc in await self._finnhub_docs(client, ticker):
                    if doc.content_hash not in existing_hashes:
                        existing_hashes.add(doc.content_hash)
                        state["raw_documents"].append(doc)
                for feed_url in NEWS_RSS_FEEDS:
                    for doc in self._rss_docs(ticker, feed_url):
                        if doc.content_hash not in existing_hashes:
                            existing_hashes.add(doc.content_hash)
                            state["raw_documents"].append(doc)
        return state

    async def _finnhub_docs(self, client: httpx.AsyncClient, ticker: str) -> list[RawDocument]:
        if not FINNHUB_API_KEY:
            return []
        cache_key = f"news:finnhub:{ticker}"
        cached = await self.cache.get(cache_key)
        if cached:
            return [RawDocument.model_validate(item) for item in cached]

        to_dt = datetime.now(UTC)
        from_dt = to_dt - timedelta(hours=NEWS_LOOKBACK_HOURS)
        params = {
            "symbol": ticker,
            "from": from_dt.date().isoformat(),
            "to": to_dt.date().isoformat(),
            "token": FINNHUB_API_KEY,
        }
        response = await client.get(
            "https://finnhub.io/api/v1/company-news",
            params=params,
        )
        if response.status_code == 403:
            raise RuntimeError("Finnhub returned 403; check API key")
        response.raise_for_status()

        payload = response.json()
        docs: list[RawDocument] = []
        if not isinstance(payload, list):
            return docs

        for item in payload[:NEWS_MAX_ARTICLES_PER_TICKER]:
            if not isinstance(item, dict):
                continue
            headline = item.get("headline", "")
            summary = item.get("summary", "")
            url = item.get("url", "")
            content = f"{headline}\n{summary}".strip()
            if not content or not url:
                continue
            docs.append(
                self._build_doc(
                    ticker=ticker,
                    title=headline or f"{ticker} article",
                    content=content,
                    url=url,
                    source_name="finnhub",
                )
            )

        await self.cache.set(
            cache_key,
            [doc.model_dump(mode="json") for doc in docs],
            ttl=CACHE_TTL_NEWS,
        )
        return docs
