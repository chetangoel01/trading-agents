from __future__ import annotations

from main import bootstrap_metadata, build_initial_state
from scheduler import RunKind


def test_bootstrap_metadata_applies_run_kind_and_execution_flag() -> None:
    metadata = bootstrap_metadata(
        "schedule",
        run_kind=RunKind.ANALYSIS_ONLY,
        execution_enabled=False,
        run_mode="continuous",
    )
    assert metadata.trigger == "schedule"
    assert metadata.schedule_run_kind == "analysis_only"
    assert metadata.execution_enabled is False
    assert metadata.run_mode == "continuous"


def test_build_initial_state_seeds_portfolio_capital() -> None:
    metadata = bootstrap_metadata("manual")
    state = build_initial_state(metadata)
    assert state["portfolio"].cash == 100000.0
    assert state["portfolio"].total_value == 100000.0
    assert state["metadata"].run_id
