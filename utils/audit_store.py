"""SQLite audit storage for run metadata and LLM call indexing."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from config import AUDIT_DB_PATH


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS llm_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    ts_utc TEXT NOT NULL,
    model TEXT NOT NULL,
    role TEXT NOT NULL,
    ticker TEXT,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    latency_ms INTEGER NOT NULL,
    success INTEGER NOT NULL,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_llm_calls_run_id ON llm_calls(run_id);
CREATE INDEX IF NOT EXISTS idx_llm_calls_role_ts ON llm_calls(role, ts_utc);
CREATE INDEX IF NOT EXISTS idx_llm_calls_success_ts ON llm_calls(success, ts_utc);

CREATE TABLE IF NOT EXISTS run_records (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    trigger TEXT NOT NULL,
    run_mode TEXT NOT NULL,
    run_kind TEXT,
    execution_enabled INTEGER NOT NULL,
    status TEXT NOT NULL,
    warnings_count INTEGER NOT NULL DEFAULT 0,
    errors_count INTEGER NOT NULL DEFAULT 0,
    total_cost_usd REAL NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_run_records_started_at ON run_records(started_at DESC);
"""


@contextmanager
def _connect(path: str) -> Iterator[sqlite3.Connection]:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        yield conn
    finally:
        conn.close()


def ensure_schema(path: str = AUDIT_DB_PATH) -> None:
    with _connect(path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()


def insert_llm_call(
    *,
    run_id: str,
    model: str,
    role: str,
    ticker: str | None,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    latency_ms: int,
    success: bool,
    error: str | None = None,
    path: str = AUDIT_DB_PATH,
) -> None:
    ensure_schema(path=path)
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO llm_calls (
                run_id, ts_utc, model, role, ticker, input_tokens, output_tokens,
                cost_usd, latency_ms, success, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                datetime.now(UTC).isoformat(),
                model,
                role,
                ticker,
                input_tokens,
                output_tokens,
                cost_usd,
                latency_ms,
                1 if success else 0,
                error,
            ),
        )
        conn.commit()


def insert_run_record_start(
    *,
    run_id: str,
    started_at: datetime,
    trigger: str,
    run_mode: str,
    run_kind: str | None,
    execution_enabled: bool,
    path: str = AUDIT_DB_PATH,
) -> None:
    ensure_schema(path=path)
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO run_records (
                run_id, started_at, trigger, run_mode, run_kind, execution_enabled, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                started_at=excluded.started_at,
                trigger=excluded.trigger,
                run_mode=excluded.run_mode,
                run_kind=excluded.run_kind,
                execution_enabled=excluded.execution_enabled,
                status=excluded.status
            """,
            (
                run_id,
                started_at.isoformat(),
                trigger,
                run_mode,
                run_kind,
                1 if execution_enabled else 0,
                "running",
            ),
        )
        conn.commit()


def finalize_run_record(
    *,
    run_id: str,
    status: str,
    warnings_count: int,
    errors_count: int,
    total_cost_usd: float,
    completed_at: datetime | None = None,
    path: str = AUDIT_DB_PATH,
) -> None:
    ensure_schema(path=path)
    completed_at = completed_at or datetime.now(UTC)
    with _connect(path) as conn:
        conn.execute(
            """
            UPDATE run_records
            SET completed_at = ?,
                status = ?,
                warnings_count = ?,
                errors_count = ?,
                total_cost_usd = ?
            WHERE run_id = ?
            """,
            (
                completed_at.isoformat(),
                status,
                warnings_count,
                errors_count,
                total_cost_usd,
                run_id,
            ),
        )
        conn.commit()


def list_recent_runs(*, limit: int = 50, path: str = AUDIT_DB_PATH) -> list[dict[str, Any]]:
    ensure_schema(path=path)
    with _connect(path) as conn:
        rows = conn.execute(
            """
            SELECT run_id, started_at, completed_at, trigger, run_mode, run_kind,
                   execution_enabled, status, warnings_count, errors_count, total_cost_usd
            FROM run_records
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        {
            "run_id": row[0],
            "started_at": row[1],
            "completed_at": row[2],
            "trigger": row[3],
            "run_mode": row[4],
            "run_kind": row[5],
            "execution_enabled": bool(row[6]),
            "status": row[7],
            "warnings_count": row[8],
            "errors_count": row[9],
            "total_cost_usd": row[10],
        }
        for row in rows
    ]
