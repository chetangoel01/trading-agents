from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from main import build_initial_state, bootstrap_metadata
from utils.audit_store import ensure_schema as ensure_audit_schema
from utils.audit_store import finalize_run_record
from utils.audit_store import insert_llm_call
from utils.audit_store import insert_run_record_start
from utils.audit_store import list_recent_runs
from utils.checkpoint_store import hydrate_state, load_checkpoint, save_checkpoint


def test_checkpoint_roundtrip(tmp_path: Path) -> None:
    db = tmp_path / "checkpoints.db"
    payload = {"metadata": {"run_id": "r1"}, "decisions": []}
    save_checkpoint("r1", payload, path=str(db))
    loaded = load_checkpoint("r1", path=str(db))
    assert loaded == payload


def test_audit_insert_creates_rows(tmp_path: Path) -> None:
    db = tmp_path / "trading.db"
    ensure_audit_schema(path=str(db))
    insert_llm_call(
        run_id="run-1",
        model="qwen/qwen3-coder",
        role="extraction",
        ticker="AAPL",
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.01,
        latency_ms=1200,
        success=True,
        path=str(db),
    )
    assert db.exists()


def test_checkpoint_hydrate_roundtrip_typed_state(tmp_path: Path) -> None:
    db = tmp_path / "checkpoints.db"
    metadata = bootstrap_metadata("manual")
    metadata.started_at = datetime.now(UTC)
    state = build_initial_state(metadata)
    payload = {
        "metadata": state["metadata"].model_dump(mode="json"),
        "raw_documents": [],
        "technical_data": [],
        "extracted_signals": [],
        "strategy_signals": [],
        "theses": [],
        "decisions": [],
        "orders": [],
        "portfolio": state["portfolio"].model_dump(mode="json"),
        "feedback": state["feedback"].model_dump(mode="json"),
        "formatted_report": state["formatted_report"],
    }
    save_checkpoint(metadata.run_id, payload, path=str(db))
    loaded = load_checkpoint(metadata.run_id, path=str(db))
    assert loaded is not None
    hydrated = hydrate_state(loaded)
    assert hydrated["metadata"].run_id == metadata.run_id
    assert hydrated["portfolio"].cash == 100000.0


def test_run_record_roundtrip_for_dashboard_queries(tmp_path: Path) -> None:
    db = tmp_path / "trading.db"
    ensure_audit_schema(path=str(db))
    insert_run_record_start(
        run_id="run-42",
        started_at=datetime(2026, 3, 18, 14, 30, tzinfo=UTC),
        trigger="schedule",
        run_mode="continuous",
        run_kind="full_execution",
        execution_enabled=True,
        path=str(db),
    )
    finalize_run_record(
        run_id="run-42",
        status="completed",
        warnings_count=1,
        errors_count=0,
        total_cost_usd=0.42,
        path=str(db),
    )
    rows = list_recent_runs(limit=10, path=str(db))
    assert len(rows) == 1
    row = rows[0]
    assert row["run_id"] == "run-42"
    assert row["status"] == "completed"
    assert row["warnings_count"] == 1
    assert row["errors_count"] == 0
    assert row["total_cost_usd"] == 0.42
