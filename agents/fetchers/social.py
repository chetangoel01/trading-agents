from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib

import httpx

from agents.base import BaseAgent
from config import CACHE_TTL_SOCIAL, SOCIAL_LOOKBACK_HOURS, SOCIAL_MIN_UPVOTES, SOCIAL_SUBREDDITS
from state import AgentState, DataSourceType, RawDocument
from utils.cache import Cache


class SocialFetcherAgent(BaseAgent):
    name = "fetch_social"

    def __init__(self) -> None:
        super().__init__()
        self.cache = Cache()

    @staticmethod
    def _hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _mentions_ticker(text: str, ticker: str) -> bool:
        upper = text.upper()
        t = ticker.upper()
        return f" {t} " in f" {upper} " or f"${t}" in upper

    @classmethod
    def _is_relevant_post(cls, post: dict, ticker: str, *, now_utc: datetime) -> bool:
        score = int(post.get("score", 0))
        if score < SOCIAL_MIN_UPVOTES:
            return False
        created_utc = int(post.get("created_utc", 0))
        created_dt = datetime.fromtimestamp(created_utc, tz=UTC)
        if now_utc - created_dt > timedelta(hours=SOCIAL_LOOKBACK_HOURS):
            return False
        text = f"{post.get('title', '')}\n{post.get('selftext', '')}"
        return cls._mentions_ticker(text, ticker)

    @classmethod
    def _post_to_document(cls, post: dict, ticker: str) -> RawDocument:
        title = post.get("title", "")
        body = post.get("selftext", "")
        content = f"{title}\n{body}".strip()
        url = f"https://reddit.com{post.get('permalink', '')}"
        return RawDocument(
            source_type=DataSourceType.SOCIAL_POST,
            ticker=ticker,
            title=title or f"{ticker} social post",
            content=content,
            url=url,
            published_at=datetime.fromtimestamp(int(post.get("created_utc", 0)), tz=UTC),
            content_hash=cls._hash(content),
            metadata={
                "upvotes": int(post.get("score", 0)),
                "subreddit": post.get("subreddit", ""),
                "comment_count": int(post.get("num_comments", 0)),
                "author": post.get("author", ""),
            },
        )

    async def _fetch_reddit_posts(
        self, client: httpx.AsyncClient, subreddit: str, ticker: str
    ) -> list[RawDocument]:
        cache_key = f"social:reddit:{subreddit}:{ticker}"
        cached = await self.cache.get(cache_key)
        if cached:
            return [RawDocument.model_validate(x) for x in cached]

        url = f"https://www.reddit.com/r/{subreddit}/search.json"
        params = {"q": ticker, "restrict_sr": "on", "sort": "new", "limit": 25}
        headers = {"User-Agent": "trading-agents/0.1"}
        response = await client.get(url, params=params, headers=headers)
        if response.status_code >= 400:
            return []
        payload = response.json()
        children = payload.get("data", {}).get("children", [])
        now = datetime.now(UTC)
        docs: list[RawDocument] = []
        for child in children:
            post = child.get("data", {}) if isinstance(child, dict) else {}
            if not isinstance(post, dict):
                continue
            if not self._is_relevant_post(post, ticker, now_utc=now):
                continue
            docs.append(self._post_to_document(post, ticker))

        await self.cache.set(cache_key, [d.model_dump(mode="json") for d in docs], ttl=CACHE_TTL_SOCIAL)
        return docs

    async def _execute(self, state: AgentState) -> AgentState:
        existing_hashes = {doc.content_hash for doc in state["raw_documents"]}
        async with httpx.AsyncClient(timeout=30.0) as client:
            for ticker in state["metadata"].tickers:
                for subreddit in SOCIAL_SUBREDDITS:
                    docs = await self._fetch_reddit_posts(client, subreddit, ticker)
                    for doc in docs:
                        if doc.content_hash in existing_hashes:
                            continue
                        existing_hashes.add(doc.content_hash)
                        state["raw_documents"].append(doc)
        return state
