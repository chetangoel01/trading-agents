"""SQLite checkpoint persistence used by scheduler/graph."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from config import CHECKPOINT_DB_PATH


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS checkpoints (
    run_id TEXT PRIMARY KEY,
    ts_utc TEXT NOT NULL,
    state_json TEXT NOT NULL
);
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


def ensure_schema(path: str = CHECKPOINT_DB_PATH) -> None:
    with _connect(path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()


def save_checkpoint(run_id: str, state: dict[str, Any], path: str = CHECKPOINT_DB_PATH) -> None:
    ensure_schema(path=path)
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO checkpoints (run_id, ts_utc, state_json)
            VALUES (?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET ts_utc=excluded.ts_utc, state_json=excluded.state_json
            """,
            (run_id, datetime.now(UTC).isoformat(), json.dumps(state, default=str)),
        )
        conn.commit()


def load_checkpoint(run_id: str, path: str = CHECKPOINT_DB_PATH) -> dict[str, Any] | None:
    ensure_schema(path=path)
    with _connect(path) as conn:
        row = conn.execute(
            "SELECT state_json FROM checkpoints WHERE run_id = ?",
            (run_id,),
        ).fetchone()
    if row is None:
        return None
    return json.loads(row[0])
