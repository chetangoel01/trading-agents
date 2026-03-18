"""LangGraph construction entrypoint.

This file intentionally starts as a lightweight scaffold in Phase 1.
Node wiring will be expanded incrementally by roadmap phase.
"""

from __future__ import annotations

from typing import Any


def build_graph() -> Any:
    """Build and compile the LangGraph pipeline.

    Returns:
        Compiled graph object once node implementations are added.
    """
    try:
        from langgraph.graph import StateGraph
    except Exception as exc:  # pragma: no cover - dependency availability
        raise RuntimeError("langgraph is not installed") from exc

    # Placeholder: concrete node wiring lands in subsequent roadmap tasks.
    return StateGraph(dict).compile()
