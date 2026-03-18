from __future__ import annotations

from agents.fetchers.news import NewsFetcherAgent
from agents.fetchers.sec import SECFetcherAgent
from state import FilingType


def test_sec_extract_relevant_sections_for_10k() -> None:
    text = (
        "cover page\n"
        "some intro\n"
        "ITEM 1A. Risk Factors\nrisk text\n"
        "ITEM 7. Management Discussion\nmda text\n"
    )
    extracted = SECFetcherAgent._extract_relevant_sections(text, "10-K")
    assert extracted.startswith("ITEM 1A")


def test_sec_build_raw_document_sets_hash_and_filing_type() -> None:
    doc = SECFetcherAgent._build_raw_document(
        ticker="AAPL",
        title="AAPL 10-K",
        content="hello world",
        url="https://example.com",
        filing_type="10-K",
    )
    assert doc.filing_type == FilingType.TEN_K
    assert len(doc.content_hash) == 64


def test_sec_select_filing_entries_accepts_hits_list() -> None:
    payload = {"hits": [{"url": "u1"}, {"url": "u2"}]}
    selected = SECFetcherAgent._select_filing_entries(payload)
    assert len(selected) == 2


def test_news_ticker_mention_matching() -> None:
    assert NewsFetcherAgent._mentions_ticker("AAPL beats estimates", "AAPL")
    assert NewsFetcherAgent._mentions_ticker("Huge move for $AAPL today", "AAPL")
    assert not NewsFetcherAgent._mentions_ticker("MSFT update", "AAPL")


def test_news_rss_docs_filters_by_ticker(monkeypatch) -> None:
    agent = NewsFetcherAgent()

    class _FakeParsed:
        entries = [
            {"title": "AAPL jumps", "summary": "great day", "link": "https://a"},
            {"title": "TSLA drops", "summary": "bad day", "link": "https://b"},
        ]

    monkeypatch.setattr("agents.fetchers.news.feedparser.parse", lambda _: _FakeParsed())
    docs = agent._rss_docs("AAPL", "https://feed.example")
    assert len(docs) == 1
    assert docs[0].ticker == "AAPL"
