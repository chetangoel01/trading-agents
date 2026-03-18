from __future__ import annotations

import json

from utils.trace import TraceWriter


def test_trace_writer_appends_jsonl(tmp_path) -> None:
    writer = TraceWriter("run-1", trace_dir=str(tmp_path))
    writer.write("run_start", mode="single")
    writer.write("run_end", status="ok")

    content = (tmp_path / "run-1.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(content) == 2
    first = json.loads(content[0])
    second = json.loads(content[1])
    assert first["event"] == "run_start"
    assert second["event"] == "run_end"
