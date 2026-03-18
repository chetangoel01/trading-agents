from __future__ import annotations

import operator
from typing import get_args, get_type_hints

from graph import build_graph, project_parallel_fetch_update
from state import AgentState
from state import FeedbackState, PortfolioSnapshot, RunMetadata
from datetime import UTC, datetime


def test_graph_compiles_with_parallel_fanout() -> None:
    graph = build_graph()
    assert graph is not None


def test_state_reducer_annotations_present_for_parallel_merges() -> None:
    hints = get_type_hints(AgentState, include_extras=True)
    raw_documents_ann = hints["raw_documents"]
    assert operator.add in get_args(raw_documents_ann)
    metadata_ann = hints["metadata"]
    reducer_candidates = [arg for arg in get_args(metadata_ann) if callable(arg)]
    assert reducer_candidates, "metadata must define a reducer for parallel fan-out"


def test_parallel_fetch_projection_avoids_non_reduced_keys() -> None:
    state = AgentState(
        metadata=RunMetadata(
            run_id="run-1",
            started_at=datetime.now(UTC),
            tickers=["AAPL"],
            trigger="manual",
            run_mode="single",
        ),
        raw_documents=[],
        technical_data=[],
        extracted_signals=[],
        strategy_signals=[],
        theses=[],
        decisions=[],
        orders=[],
        portfolio=PortfolioSnapshot(),
        feedback=FeedbackState(),
        formatted_report=None,
    )
    update = project_parallel_fetch_update(state)
    assert set(update.keys()) == {"raw_documents", "technical_data", "metadata"}
