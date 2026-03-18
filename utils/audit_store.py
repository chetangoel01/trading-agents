"""SQLite audit storage for run metadata and LLM call indexing."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

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
