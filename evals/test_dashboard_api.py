from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import json

from fastapi.testclient import TestClient

from main import build_initial_state, bootstrap_metadata
from state import ActionType, StrategyType, TradeOutcome
from utils.audit_store import finalize_run_record, insert_run_record_start
from utils.checkpoint_store import save_checkpoint


def _seed_checkpoint(run_id: str, checkpoint_db: Path) -> None:
    metadata = bootstrap_metadata("manual")
    metadata.run_id = run_id
    metadata.started_at = datetime(2026, 3, 18, 14, 0, tzinfo=UTC)
    state = build_initial_state(metadata)
    state["feedback"].strategy_performance = []
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
        "formatted_report": None,
    }
    save_checkpoint(run_id, payload, path=str(checkpoint_db))


def test_dashboard_portfolio_endpoint_returns_latest_snapshot(tmp_path: Path) -> None:
    from dashboard.app import create_app

    checkpoint_db = tmp_path / "checkpoints.db"
    audit_db = tmp_path / "trading.db"
    _seed_checkpoint("run-a", checkpoint_db)
    app = create_app(checkpoint_db_path=str(checkpoint_db), audit_db_path=str(audit_db))
    client = TestClient(app)

    resp = client.get("/api/portfolio")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["cash"] == 100000.0
    assert payload["total_value"] == 100000.0


def test_dashboard_runs_endpoint_returns_indexed_runs(tmp_path: Path) -> None:
    from dashboard.app import create_app

    checkpoint_db = tmp_path / "checkpoints.db"
    audit_db = tmp_path / "trading.db"
    _seed_checkpoint("run-b", checkpoint_db)
    insert_run_record_start(
        run_id="run-b",
        started_at=datetime(2026, 3, 18, 14, 30, tzinfo=UTC),
        trigger="schedule",
        run_mode="continuous",
        run_kind="full_execution",
        execution_enabled=True,
        path=str(audit_db),
    )
    finalize_run_record(
        run_id="run-b",
        status="completed",
        warnings_count=0,
        errors_count=0,
        total_cost_usd=0.07,
        path=str(audit_db),
    )

    app = create_app(checkpoint_db_path=str(checkpoint_db), audit_db_path=str(audit_db))
    client = TestClient(app)
    resp = client.get("/api/runs")
    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload) == 1
    assert payload[0]["run_id"] == "run-b"
    assert payload[0]["status"] == "completed"


def test_dashboard_strategies_endpoint_returns_list(tmp_path: Path) -> None:
    from dashboard.app import create_app

    checkpoint_db = tmp_path / "checkpoints.db"
    audit_db = tmp_path / "trading.db"
    _seed_checkpoint("run-c", checkpoint_db)
    app = create_app(checkpoint_db_path=str(checkpoint_db), audit_db_path=str(audit_db))
    client = TestClient(app)

    resp = client.get("/api/strategies")
    assert resp.status_code == 200
    payload = resp.json()
    assert isinstance(payload, list)


def test_dashboard_run_detail_endpoint_returns_checkpoint_state(tmp_path: Path) -> None:
    from dashboard.app import create_app

    checkpoint_db = tmp_path / "checkpoints.db"
    audit_db = tmp_path / "trading.db"
    _seed_checkpoint("run-detail", checkpoint_db)
    app = create_app(checkpoint_db_path=str(checkpoint_db), audit_db_path=str(audit_db))
    client = TestClient(app)

    resp = client.get("/api/runs/run-detail")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["metadata"]["run_id"] == "run-detail"


def test_dashboard_trace_endpoint_returns_jsonl_rows(tmp_path: Path) -> None:
    from dashboard.app import create_app

    checkpoint_db = tmp_path / "checkpoints.db"
    audit_db = tmp_path / "trading.db"
    trace_dir = tmp_path / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    trace_path = trace_dir / "run-trace-1.jsonl"
    trace_path.write_text(
        "\n".join(
            [
                json.dumps({"event": "run_start", "run_id": "run-trace-1"}),
                json.dumps({"event": "run_end", "run_id": "run-trace-1"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    app = create_app(
        checkpoint_db_path=str(checkpoint_db),
        audit_db_path=str(audit_db),
        trace_dir=str(trace_dir),
    )
    client = TestClient(app)
    resp = client.get("/api/runs/run-trace-1/trace")
    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload) == 2
    assert payload[0]["event"] == "run_start"


def test_dashboard_outcomes_endpoint_returns_feedback_outcomes(tmp_path: Path) -> None:
    from dashboard.app import create_app

    checkpoint_db = tmp_path / "checkpoints.db"
    audit_db = tmp_path / "trading.db"
    metadata = bootstrap_metadata("manual")
    metadata.run_id = "run-outcomes"
    metadata.started_at = datetime(2026, 3, 18, 16, 0, tzinfo=UTC)
    state = build_initial_state(metadata)
    state["feedback"].outcomes = [
        TradeOutcome(
            ticker="AAPL",
            action=ActionType.SELL,
            entry_price=100.0,
            exit_price=105.0,
            quantity=10,
            pnl_usd=50.0,
            pnl_pct=0.05,
            result="win",
            holding_duration_hours=5.0,
            strategy_attribution=StrategyType.FUNDAMENTAL,
            thesis_confidence_at_entry=0.75,
            exit_reason="take_profit",
            opened_at=datetime(2026, 3, 18, 10, 0, tzinfo=UTC),
            closed_at=datetime(2026, 3, 18, 15, 0, tzinfo=UTC),
        )
    ]
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
        "formatted_report": None,
    }
    save_checkpoint("run-outcomes", payload, path=str(checkpoint_db))
    app = create_app(checkpoint_db_path=str(checkpoint_db), audit_db_path=str(audit_db))
    client = TestClient(app)
    resp = client.get("/api/outcomes")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["ticker"] == "AAPL"
