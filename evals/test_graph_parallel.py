from __future__ import annotations

import operator
from typing import get_args, get_type_hints

from graph import build_graph
from state import AgentState


def test_graph_compiles_with_parallel_fanout() -> None:
    graph = build_graph()
    assert graph is not None


def test_state_reducer_annotations_present_for_parallel_merges() -> None:
    hints = get_type_hints(AgentState, include_extras=True)
    raw_documents_ann = hints["raw_documents"]
    assert operator.add in get_args(raw_documents_ann)
