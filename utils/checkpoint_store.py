"""SQLite checkpoint persistence used by scheduler/graph."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from config import CHECKPOINT_DB_PATH
from state import (
    AgentState,
    ExtractedSignal,
    FeedbackState,
    OrderRecord,
    PortfolioSnapshot,
    RawDocument,
    RunMetadata,
    StrategySignal,
    TechnicalSnapshot,
    TickerThesis,
    TradeDecision,
)


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


def hydrate_state(raw_state: dict[str, Any]) -> AgentState:
    """Convert JSON checkpoint payload back into typed AgentState models."""
    return AgentState(
        metadata=RunMetadata.model_validate(raw_state["metadata"]),
        raw_documents=[RawDocument.model_validate(x) for x in raw_state.get("raw_documents", [])],
        technical_data=[TechnicalSnapshot.model_validate(x) for x in raw_state.get("technical_data", [])],
        extracted_signals=[
            ExtractedSignal.model_validate(x) for x in raw_state.get("extracted_signals", [])
        ],
        strategy_signals=[StrategySignal.model_validate(x) for x in raw_state.get("strategy_signals", [])],
        theses=[TickerThesis.model_validate(x) for x in raw_state.get("theses", [])],
        decisions=[TradeDecision.model_validate(x) for x in raw_state.get("decisions", [])],
        orders=[OrderRecord.model_validate(x) for x in raw_state.get("orders", [])],
        portfolio=PortfolioSnapshot.model_validate(raw_state["portfolio"]),
        feedback=FeedbackState.model_validate(raw_state["feedback"]),
        formatted_report=raw_state.get("formatted_report"),
    )
