from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import AUDIT_DB_PATH, CHECKPOINT_DB_PATH, TRACE_DIR
from utils.audit_store import list_recent_runs
from utils.checkpoint_store import ensure_schema as ensure_checkpoint_schema
from utils.checkpoint_store import load_checkpoint


def _load_latest_state(checkpoint_db_path: str) -> dict[str, Any] | None:
    ensure_checkpoint_schema(path=checkpoint_db_path)
    db_path = Path(checkpoint_db_path)
    if not db_path.exists():
        return None
    with sqlite3.connect(checkpoint_db_path) as conn:
        row = conn.execute(
            """
            SELECT state_json
            FROM checkpoints
            ORDER BY ts_utc DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return json.loads(row[0])


def _read_trace_rows(trace_dir: str, run_id: str) -> list[dict[str, Any]]:
    path = Path(trace_dir) / f"{run_id}.jsonl"
    if not path.exists():
        raise FileNotFoundError(run_id)
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def create_app(
    *,
    checkpoint_db_path: str = CHECKPOINT_DB_PATH,
    audit_db_path: str = AUDIT_DB_PATH,
    trace_dir: str = TRACE_DIR,
) -> FastAPI:
    app = FastAPI(title="Trading Agents Dashboard API")
    frontend_dir = Path(__file__).parent / "frontend"
    if frontend_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/")
    def get_dashboard() -> FileResponse:
        index = frontend_dir / "index.html"
        if not index.exists():
            raise HTTPException(status_code=404, detail="frontend not built")
        return FileResponse(index)

    @app.get("/api/portfolio")
    def get_portfolio() -> dict[str, Any]:
        state = _load_latest_state(checkpoint_db_path)
        if state is None:
            return {}
        return state.get("portfolio", {})

    @app.get("/api/runs")
    def get_runs(limit: int = 50) -> list[dict[str, Any]]:
        return list_recent_runs(limit=limit, path=audit_db_path)

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, Any]:
        state = load_checkpoint(run_id, path=checkpoint_db_path)
        if state is None:
            raise HTTPException(status_code=404, detail="run not found")
        return state

    @app.get("/api/runs/{run_id}/trace")
    def get_run_trace(run_id: str) -> list[dict[str, Any]]:
        try:
            return _read_trace_rows(trace_dir, run_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="trace not found") from None

    @app.get("/api/strategies")
    def get_strategies() -> list[dict[str, Any]]:
        state = _load_latest_state(checkpoint_db_path)
        if state is None:
            return []
        feedback = state.get("feedback", {})
        strategies = feedback.get("strategy_performance", [])
        if not isinstance(strategies, list):
            return []
        return strategies

    @app.get("/api/outcomes")
    def get_outcomes() -> list[dict[str, Any]]:
        state = _load_latest_state(checkpoint_db_path)
        if state is None:
            return []
        feedback = state.get("feedback", {})
        outcomes = feedback.get("outcomes", [])
        if not isinstance(outcomes, list):
            return []
        return outcomes

    return app


app = create_app()
