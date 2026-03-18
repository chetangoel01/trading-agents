"""LangGraph construction entrypoint."""

from __future__ import annotations

from agents.decision import DecisionAgent
from agents.execution import ExecutionAgent
from agents.extraction import ExtractionAgent
from agents.feedback import FeedbackAgent
from agents.fetchers.market_data import MarketDataFetcherAgent
from agents.fetchers.news import NewsFetcherAgent
from agents.fetchers.sec import SECFetcherAgent
from agents.fetchers.social import SocialFetcherAgent
from agents.fetchers.transcript import TranscriptFetcherAgent
from agents.formatter import FormatterAgent
from agents.monitor import MonitorAgent
from agents.strategy import StrategyEngine
from agents.synthesis import SynthesisAgent
from state import ActionType, AgentState


def project_parallel_fetch_update(state: AgentState) -> dict:
    """Return only reducer-safe channels for parallel fetch fan-out."""
    return {
        "raw_documents": state["raw_documents"],
        "technical_data": state["technical_data"],
        "metadata": state["metadata"],
    }


def build_graph():
    """Build and compile the LangGraph pipeline."""
    try:
        from langgraph.graph import END, START, StateGraph
    except Exception as exc:  # pragma: no cover - dependency availability
        raise RuntimeError("langgraph is not installed") from exc

    sec_fetcher = SECFetcherAgent()
    news_fetcher = NewsFetcherAgent()
    transcript_fetcher = TranscriptFetcherAgent()
    social_fetcher = SocialFetcherAgent()
    market_data_fetcher = MarketDataFetcherAgent()
    extraction_agent = ExtractionAgent()
    strategy_engine = StrategyEngine()
    synthesis_agent = SynthesisAgent()
    decision_agent = DecisionAgent()
    execution_agent = ExecutionAgent()
    monitor_agent = MonitorAgent()
    feedback_agent = FeedbackAgent()
    formatter_agent = FormatterAgent()

    graph = StateGraph(AgentState)

    async def _fetch_sec_node(state: AgentState):
        return project_parallel_fetch_update(await sec_fetcher.run(state))

    async def _fetch_news_node(state: AgentState):
        return project_parallel_fetch_update(await news_fetcher.run(state))

    async def _fetch_transcripts_node(state: AgentState):
        return project_parallel_fetch_update(await transcript_fetcher.run(state))

    async def _fetch_social_node(state: AgentState):
        return project_parallel_fetch_update(await social_fetcher.run(state))

    async def _fetch_market_data_node(state: AgentState):
        return project_parallel_fetch_update(await market_data_fetcher.run(state))

    graph.add_node("fetch_sec", _fetch_sec_node)
    graph.add_node("fetch_news", _fetch_news_node)
    graph.add_node("fetch_transcripts", _fetch_transcripts_node)
    graph.add_node("fetch_social", _fetch_social_node)
    graph.add_node("fetch_market_data", _fetch_market_data_node)
    graph.add_node("extract", extraction_agent.run)
    graph.add_node("strategize", strategy_engine.run)
    graph.add_node("synthesize", synthesis_agent.run)
    graph.add_node("decide", decision_agent.run)
    graph.add_node("execute", execution_agent.run)
    graph.add_node("monitor", monitor_agent.run)
    graph.add_node("feedback", feedback_agent.run)
    graph.add_node("format", formatter_agent.run)

    # Parallel fetch fan-out from START.
    graph.add_edge(START, "fetch_sec")
    graph.add_edge(START, "fetch_news")
    graph.add_edge(START, "fetch_transcripts")
    graph.add_edge(START, "fetch_social")
    graph.add_edge(START, "fetch_market_data")

    # Fan-in to extraction.
    graph.add_edge("fetch_sec", "extract")
    graph.add_edge("fetch_news", "extract")
    graph.add_edge("fetch_transcripts", "extract")
    graph.add_edge("fetch_social", "extract")
    graph.add_edge("fetch_market_data", "extract")
    graph.add_edge("extract", "strategize")
    graph.add_edge("strategize", "synthesize")
    graph.add_edge("synthesize", "decide")
    graph.add_conditional_edges(
        "decide",
        route_after_decision,
        {
            "execute": "execute",
            "skip_to_feedback": "feedback",
        },
    )
    graph.add_edge("execute", "monitor")
    graph.add_edge("monitor", "feedback")
    graph.add_edge("feedback", "format")
    graph.add_edge("format", END)
    return graph.compile()


def route_after_decision(state: AgentState) -> str:
    actionable = [d for d in state["decisions"] if d.action != ActionType.HOLD]
    return "execute" if actionable else "skip_to_feedback"
