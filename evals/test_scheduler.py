from __future__ import annotations

from datetime import UTC, datetime
import os
from pathlib import Path

from events.bus import EventBus
from scheduler import (
    ContinuousScheduler,
    RunKind,
    classify_run_time,
    cleanup_old_traces,
    make_schedule_decision,
)


def test_classify_premarket_analysis_window() -> None:
    dt = datetime(2026, 3, 18, 13, 0, tzinfo=UTC)  # 9:00 ET
    assert classify_run_time(dt) == RunKind.ANALYSIS_ONLY


def test_classify_regular_execution_window() -> None:
    dt = datetime(2026, 3, 18, 14, 30, tzinfo=UTC)  # 10:30 ET
    assert classify_run_time(dt) == RunKind.FULL_EXECUTION


def test_classify_postclose_feedback_window() -> None:
    dt = datetime(2026, 3, 18, 20, 15, tzinfo=UTC)  # 4:15 ET
    assert classify_run_time(dt) == RunKind.FEEDBACK_ONLY


def test_classify_non_window_time() -> None:
    dt = datetime(2026, 3, 18, 18, 47, tzinfo=UTC)  # 2:47 ET
    assert classify_run_time(dt) == RunKind.NONE


def test_schedule_decision_disables_execution_for_analysis_only() -> None:
    dt = datetime(2026, 3, 18, 13, 0, tzinfo=UTC)  # 9:00 ET
    decision = make_schedule_decision(dt)
    assert decision.run_kind == RunKind.ANALYSIS_ONLY
    assert decision.should_execute_orders is False


def test_schedule_decision_enables_execution_in_main_window() -> None:
    dt = datetime(2026, 3, 18, 15, 30, tzinfo=UTC)  # 11:30 ET
    decision = make_schedule_decision(dt)
    assert decision.run_kind == RunKind.FULL_EXECUTION
    assert decision.should_execute_orders is True


def test_cleanup_old_traces_deletes_files_older_than_retention(tmp_path: Path) -> None:
    old_file = tmp_path / "old.jsonl"
    old_file.write_text("x", encoding="utf-8")
    old_dt = datetime(2025, 1, 1, tzinfo=UTC).timestamp()
    os.utime(old_file, times=(old_dt, old_dt))

    fresh_file = tmp_path / "fresh.jsonl"
    fresh_file.write_text("y", encoding="utf-8")
    fresh_dt = datetime(2026, 3, 10, tzinfo=UTC).timestamp()
    os.utime(fresh_file, times=(fresh_dt, fresh_dt))

    deleted = cleanup_old_traces(
        trace_dir=tmp_path,
        retention_days=90,
        now_utc=datetime(2026, 3, 18, tzinfo=UTC),
    )

    assert old_file in deleted
    assert not old_file.exists()
    assert fresh_file.exists()


async def test_scheduler_emits_event_once_per_time_slot() -> None:
    bus = EventBus()
    seen: list[RunKind] = []

    async def _handle(payload):
        seen.append(payload["decision"].run_kind)

    bus.subscribe("schedule", _handle)
    scheduler = ContinuousScheduler(event_bus=bus, event_name="schedule")
    slot = datetime(2026, 3, 18, 14, 0, tzinfo=UTC)  # 10:00 ET
    await scheduler._maybe_trigger_pipeline(slot)
    await scheduler._maybe_trigger_pipeline(slot)
    assert seen == [RunKind.FULL_EXECUTION]


async def test_scheduler_falls_back_to_callback_when_no_event_bus() -> None:
    seen: list[RunKind] = []

    async def _cb(decision):
        seen.append(decision.run_kind)

    scheduler = ContinuousScheduler(on_trigger=_cb)
    slot = datetime(2026, 3, 18, 13, 0, tzinfo=UTC)  # 9:00 ET
    await scheduler._maybe_trigger_pipeline(slot)
    assert seen == [RunKind.ANALYSIS_ONLY]
