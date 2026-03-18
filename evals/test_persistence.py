from __future__ import annotations

from pathlib import Path

from utils.audit_store import ensure_schema as ensure_audit_schema
from utils.audit_store import insert_llm_call
from utils.checkpoint_store import load_checkpoint, save_checkpoint


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
