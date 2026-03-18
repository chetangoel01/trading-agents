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


def build_graph():
    """Build and compile the LangGraph pipeline."""
    try:
        from langgraph.graph import StateGraph
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
    graph.add_node("fetch_sec", sec_fetcher.run)
    graph.add_node("fetch_news", news_fetcher.run)
    graph.add_node("fetch_transcripts", transcript_fetcher.run)
    graph.add_node("fetch_social", social_fetcher.run)
    graph.add_node("fetch_market_data", market_data_fetcher.run)
    graph.add_node("extract", extraction_agent.run)
    graph.add_node("strategize", strategy_engine.run)
    graph.add_node("synthesize", synthesis_agent.run)
    graph.add_node("decide", decision_agent.run)
    graph.add_node("execute", execution_agent.run)
    graph.add_node("monitor", monitor_agent.run)
    graph.add_node("feedback", feedback_agent.run)
    graph.add_node("format", formatter_agent.run)

    graph.set_entry_point("fetch_sec")
    graph.add_edge("fetch_sec", "fetch_news")
    graph.add_edge("fetch_news", "fetch_transcripts")
    graph.add_edge("fetch_transcripts", "fetch_social")
    graph.add_edge("fetch_social", "fetch_market_data")
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
    graph.set_finish_point("format")
    return graph.compile()


def route_after_decision(state: AgentState) -> str:
    actionable = [d for d in state["decisions"] if d.action != ActionType.HOLD]
    return "execute" if actionable else "skip_to_feedback"
