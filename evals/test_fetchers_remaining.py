from __future__ import annotations

from datetime import UTC, datetime, timedelta

from agents.fetchers.market_data import MarketDataFetcherAgent
from agents.fetchers.social import SocialFetcherAgent
from agents.fetchers.transcript import TranscriptFetcherAgent
from state import DataSourceType


def test_transcript_extract_key_sections() -> None:
    text = (
        "intro text\n"
        "CEO Remarks\nour business improved\n"
        "CFO Remarks\nmargin expanded\n"
        "Q&A\nanalyst question and answer\n"
    )
    extracted = TranscriptFetcherAgent._extract_key_sections(text)
    assert "CEO Remarks" in extracted
    assert "CFO Remarks" in extracted
    assert "Q&A" in extracted


def test_social_post_filter_by_upvotes_and_lookback() -> None:
    now = datetime.now(UTC)
    post = {
        "title": "AAPL is interesting",
        "selftext": "strong quarter",
        "score": 150,
        "created_utc": int((now - timedelta(hours=2)).timestamp()),
        "num_comments": 12,
        "subreddit": "stocks",
        "author": "user1",
        "permalink": "/r/stocks/comments/abc/aapl/",
    }
    assert SocialFetcherAgent._is_relevant_post(post, "AAPL", now_utc=now) is True


def test_social_post_to_raw_document() -> None:
    now = datetime.now(UTC)
    post = {
        "title": "AAPL rocket",
        "selftext": "to the moon",
        "score": 200,
        "created_utc": int(now.timestamp()),
        "num_comments": 10,
        "subreddit": "stocks",
        "author": "user1",
        "permalink": "/r/stocks/comments/abc/aapl/",
    }
    doc = SocialFetcherAgent._post_to_document(post, "AAPL")
    assert doc.source_type == DataSourceType.SOCIAL_POST
    assert doc.ticker == "AAPL"
    assert "AAPL rocket" in doc.content


def test_market_data_indicator_snapshot_derivations() -> None:
    closes = [100 + i for i in range(220)]
    volumes = [1_000_000 + i * 100 for i in range(220)]
    snapshot = MarketDataFetcherAgent._snapshot_from_bars(
        ticker="AAPL",
        closes=closes,
        volumes=volumes,
        as_of=datetime.now(UTC),
    )
    assert snapshot.ticker == "AAPL"
    assert snapshot.sma_20 is not None
    assert snapshot.sma_50 is not None
    assert snapshot.sma_200 is not None
    assert snapshot.price_vs_sma_200 in {"above", "below"}
    assert snapshot.rsi_zone in {"oversold", "neutral", "overbought"}
