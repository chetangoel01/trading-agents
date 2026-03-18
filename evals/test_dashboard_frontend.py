from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from dashboard.app import create_app


def test_dashboard_root_serves_html(tmp_path: Path) -> None:
    app = create_app(
        checkpoint_db_path=str(tmp_path / "checkpoints.db"),
        audit_db_path=str(tmp_path / "trading.db"),
    )
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Trading Agents Dashboard" in resp.text


def test_dashboard_static_assets_served(tmp_path: Path) -> None:
    app = create_app(
        checkpoint_db_path=str(tmp_path / "checkpoints.db"),
        audit_db_path=str(tmp_path / "trading.db"),
    )
    client = TestClient(app)
    resp = client.get("/static/styles.css")
    assert resp.status_code == 200
    assert "text/css" in resp.headers["content-type"]
