"""Scheduling utilities and continuous-mode control flow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
import asyncio
from collections.abc import Awaitable, Callable
from zoneinfo import ZoneInfo

from config import (
    CANONICAL_TZ,
    SCHEDULE_TRACE_CLEANUP,
    TRACE_DIR,
    TRACE_RETENTION_DAYS,
    SCHEDULE_EXECUTION_END,
    SCHEDULE_EXECUTION_START,
    SCHEDULE_INTERVAL_MINUTES,
    SCHEDULE_POSTCLOSE_FEEDBACK,
    SCHEDULE_PREMARKET_ANALYSIS,
)


class RunKind(str, Enum):
    ANALYSIS_ONLY = "analysis_only"
    FULL_EXECUTION = "full_execution"
    FEEDBACK_ONLY = "feedback_only"
    NONE = "none"


@dataclass(frozen=True)
class ScheduleDecision:
    run_kind: RunKind
    should_execute_orders: bool
    reason: str


def _parse_hhmm(value: str) -> tuple[int, int]:
    hour_str, minute_str = value.split(":")
    return int(hour_str), int(minute_str)


def _is_exact_hhmm(local_dt: datetime, hhmm: str) -> bool:
    hour, minute = _parse_hhmm(hhmm)
    return local_dt.hour == hour and local_dt.minute == minute


def _is_execution_slot(local_dt: datetime) -> bool:
    start_hour, start_minute = _parse_hhmm(SCHEDULE_EXECUTION_START)
    end_hour, end_minute = _parse_hhmm(SCHEDULE_EXECUTION_END)
    start = local_dt.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
    end = local_dt.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
    if local_dt < start or local_dt > end:
        return False
    minutes_since_start = int((local_dt - start).total_seconds() // 60)
    return minutes_since_start % SCHEDULE_INTERVAL_MINUTES == 0


def classify_run_time(now_utc: datetime | None = None) -> RunKind:
    """Classify the schedule slot for the current UTC timestamp."""
    now_utc = now_utc or datetime.now(UTC)
    local_dt = now_utc.astimezone(ZoneInfo(CANONICAL_TZ))

    if _is_exact_hhmm(local_dt, SCHEDULE_PREMARKET_ANALYSIS):
        return RunKind.ANALYSIS_ONLY

    if _is_execution_slot(local_dt):
        return RunKind.FULL_EXECUTION

    if _is_exact_hhmm(local_dt, SCHEDULE_POSTCLOSE_FEEDBACK):
        return RunKind.FEEDBACK_ONLY

    return RunKind.NONE


def make_schedule_decision(now_utc: datetime | None = None) -> ScheduleDecision:
    run_kind = classify_run_time(now_utc)
    if run_kind == RunKind.FULL_EXECUTION:
        return ScheduleDecision(
            run_kind=run_kind,
            should_execute_orders=True,
            reason="in regular execution window",
        )
    if run_kind in {RunKind.ANALYSIS_ONLY, RunKind.FEEDBACK_ONLY}:
        return ScheduleDecision(
            run_kind=run_kind,
            should_execute_orders=False,
            reason="schedule window is non-execution",
        )
    return ScheduleDecision(
        run_kind=run_kind,
        should_execute_orders=False,
        reason="outside configured schedule windows",
    )


def cleanup_old_traces(
    trace_dir: str | Path,
    retention_days: int,
    now_utc: datetime | None = None,
) -> list[Path]:
    """Delete jsonl trace files older than retention policy."""
    now_utc = now_utc or datetime.now(UTC)
    cutoff = now_utc - timedelta(days=retention_days)
    trace_dir_path = Path(trace_dir)
    if not trace_dir_path.exists():
        return []

    deleted: list[Path] = []
    for file_path in trace_dir_path.glob("*.jsonl"):
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=UTC)
        if mtime < cutoff:
            file_path.unlink(missing_ok=True)
            deleted.append(file_path)
    return deleted


class ContinuousScheduler:
    """Minimal scheduler loop that emits callbacks on schedule windows."""

    def __init__(
        self,
        on_trigger: Callable[[ScheduleDecision], Awaitable[None]] | None = None,
        *,
        event_bus=None,
        event_name: str = "schedule",
        tick_seconds: int = 30,
    ) -> None:
        self.on_trigger = on_trigger
        self.event_bus = event_bus
        self.event_name = event_name
        self.tick_seconds = tick_seconds
        self._last_trigger_key: str | None = None
        self._last_cleanup_date: str | None = None

    async def run_forever(self) -> None:
        while True:
            now_utc = datetime.now(UTC)
            await self._maybe_run_trace_cleanup(now_utc)
            await self._maybe_trigger_pipeline(now_utc)
            await asyncio.sleep(self.tick_seconds)

    async def _maybe_trigger_pipeline(self, now_utc: datetime) -> None:
        decision = make_schedule_decision(now_utc)
        if decision.run_kind == RunKind.NONE:
            return
        local_dt = now_utc.astimezone(ZoneInfo(CANONICAL_TZ))
        trigger_key = f"{local_dt.date().isoformat()}:{local_dt.hour:02d}:{local_dt.minute:02d}"
        if trigger_key == self._last_trigger_key:
            return
        self._last_trigger_key = trigger_key
        if self.event_bus is not None:
            await self.event_bus.emit(
                self.event_name,
                {
                    "decision": decision,
                    "scheduled_at_utc": now_utc.isoformat(),
                },
            )
            return
        if self.on_trigger is not None:
            await self.on_trigger(decision)

    async def _maybe_run_trace_cleanup(self, now_utc: datetime) -> None:
        local_dt = now_utc.astimezone(ZoneInfo(CANONICAL_TZ))
        if not _is_exact_hhmm(local_dt, SCHEDULE_TRACE_CLEANUP):
            return
        if self._last_cleanup_date == local_dt.date().isoformat():
            return
        cleanup_old_traces(
            trace_dir=TRACE_DIR,
            retention_days=TRACE_RETENTION_DAYS,
            now_utc=now_utc,
        )
        self._last_cleanup_date = local_dt.date().isoformat()
