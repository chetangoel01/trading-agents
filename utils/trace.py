"""JSONL trace writer for run observability."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from config import TRACE_DIR


class TraceWriter:
    def __init__(self, run_id: str, trace_dir: str = TRACE_DIR) -> None:
        self.run_id = run_id
        self.trace_path = Path(trace_dir) / f"{run_id}.jsonl"
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: str, **payload: Any) -> None:
        row = {
            "ts": datetime.now(UTC).isoformat(),
            "event": event,
            **payload,
        }
        with self.trace_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, default=str))
            f.write("\n")
