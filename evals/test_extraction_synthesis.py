from __future__ import annotations

from datetime import UTC, datetime

from agents.extraction import ExtractionAgent
from agents.synthesis import SynthesisAgent
from state import (
    AgentState,
    DataSourceType,
    FeedbackState,
    PortfolioSnapshot,
    RawDocument,
    RunMetadata,
    StrategySignal,
    StrategyType,
)


class _Meta:
    def __init__(self, model: str = "test-model") -> None:
        self.model = model
        self.input_tokens = 100
        self.output_tokens = 50
        self.latency_ms = 10
        self.estimated_cost_usd = 0.01


def _state_with_docs() -> AgentState:
    return AgentState(
        metadata=RunMetadata(
            run_id="run-1",
            started_at=datetime.now(UTC),
            tickers=["AAPL", "MSFT"],
            trigger="manual",
            run_mode="single",
        ),
        raw_documents=[
            RawDocument(
                source_type=DataSourceType.NEWS_ARTICLE,
                ticker="AAPL",
                title="AAPL news",
                content="AAPL revenue grew strongly",
                url="https://a",
                content_hash="h1",
            ),
            RawDocument(
                source_type=DataSourceType.NEWS_ARTICLE,
                ticker="MSFT",
                title="MSFT news",
                content="MSFT article",
                url="https://m",
                content_hash="h2",
            ),
        ],
        technical_data=[],
        extracted_signals=[],
        strategy_signals=[],
        theses=[],
        decisions=[],
        orders=[],
        portfolio=PortfolioSnapshot(
            cash=100000.0,
            equity=0.0,
            total_value=100000.0,
            peak_portfolio_value=100000.0,
        ),
        feedback=FeedbackState(),
        formatted_report=None,
    )


async def test_extraction_isolates_failures_per_ticker(monkeypatch) -> None:
    agent = ExtractionAgent()
    state = _state_with_docs()

    async def _fake_call(ticker: str, content: str):
        if ticker == "MSFT":
            raise RuntimeError("model timeout")
        return (
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"metrics":[{"name":"revenue","value":10,"unit":"USD_millions","period":"Q1"}],'
                            '"sentiments":[{"direction":"bullish","confidence":0.8,"key_phrase":"revenue grew","context":"news"}],'
                            '"risks":[],"key_events":["earnings"],"management_guidance":null,"insider_activity":"none"}'
                        }
                    }
                ]
            },
            _Meta(),
        )

    monkeypatch.setattr(agent, "_call_extraction_llm", _fake_call)
    result = await agent._execute(state)
    assert len(result["extracted_signals"]) == 1
    assert result["extracted_signals"][0].ticker == "AAPL"
    assert any("MSFT" in str(w) for w in result["metadata"].warnings)


def _state_for_synthesis() -> AgentState:
    state = _state_with_docs()
    state["extracted_signals"] = []
    state["strategy_signals"] = [
        StrategySignal(
            strategy=StrategyType.FUNDAMENTAL,
            ticker="AAPL",
            direction="bullish",
            confidence=0.9,
            reasoning="strong earnings",
            time_horizon="weeks",
        )
    ]
    return state


async def test_synthesis_falls_back_to_neutral_for_failed_ticker(monkeypatch) -> None:
    agent = SynthesisAgent()
    state = _state_for_synthesis()

    async def _fake_call(ticker: str, payload: dict):
        if ticker == "MSFT":
            raise RuntimeError("provider unavailable")
        return (
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"direction":"bullish","confidence":0.77,"summary":"positive",'
                            '"bull_case":"growth","bear_case":"valuation",'
                            '"key_catalysts":["ai demand"],"key_risks":["macro"],'
                            '"dominant_strategy":"fundamental","sector":"technology"}'
                        }
                    }
                ]
            },
            _Meta(),
        )

    monkeypatch.setattr(agent, "_call_synthesis_llm", _fake_call)
    result = await agent._execute(state)
    assert len(result["theses"]) == 2
    aapl = [t for t in result["theses"] if t.ticker == "AAPL"][0]
    msft = [t for t in result["theses"] if t.ticker == "MSFT"][0]
    assert aapl.confidence == 0.77
    assert msft.confidence == 0.0
    assert msft.direction.value == "neutral"
