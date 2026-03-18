"""CLI entrypoint for single/continuous/backtest modes."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import uuid

from config import RUN_MODE, WATCHLIST, validate_config
from events.bus import EventBus
from graph import build_graph
from scheduler import ContinuousScheduler, RunKind
from state import AgentState, FeedbackState, PortfolioSnapshot, RunMetadata
from utils.checkpoint_store import save_checkpoint
from utils.logger import get_logger
from utils.trace import TraceWriter


def bootstrap_metadata(
    trigger: str = "manual",
    *,
    run_kind: RunKind | None = None,
    execution_enabled: bool = True,
    run_mode: str = RUN_MODE,
) -> RunMetadata:
    return RunMetadata(
        run_id=str(uuid.uuid4()),
        started_at=datetime.now(UTC),
        tickers=WATCHLIST,
        trigger=trigger,
        run_mode=run_mode,
        schedule_run_kind=run_kind.value if run_kind else None,
        execution_enabled=execution_enabled,
    )


def build_initial_state(metadata: RunMetadata) -> AgentState:
    return AgentState(
        metadata=metadata,
        raw_documents=[],
        technical_data=[],
        extracted_signals=[],
        strategy_signals=[],
        theses=[],
        decisions=[],
        orders=[],
        portfolio=PortfolioSnapshot(
            cash=100000.0,
            equity=0.0,
            total_value=100000.0,
            peak_portfolio_value=100000.0,
        ),
        feedback=FeedbackState(),
        formatted_report=None,
    )


async def run_pipeline_once(
    *,
    trigger: str,
    run_kind: RunKind | None,
    execution_enabled: bool,
    run_mode: str,
) -> AgentState:
    logger = get_logger("main")
    metadata = bootstrap_metadata(
        trigger,
        run_kind=run_kind,
        execution_enabled=execution_enabled,
        run_mode=run_mode,
    )
    state = build_initial_state(metadata)
    trace = TraceWriter(metadata.run_id)
    trace.write(
        "run_start",
        run_id=metadata.run_id,
        mode=run_mode,
        trigger=trigger,
        run_kind=metadata.schedule_run_kind,
        execution_enabled=execution_enabled,
        tickers=metadata.tickers,
    )
    logger.info(
        "run_start",
        extra={
            "extra": {
                "run_id": metadata.run_id,
                "run_mode": run_mode,
                "trigger": trigger,
                "run_kind": metadata.schedule_run_kind,
                "execution_enabled": execution_enabled,
                "tickers": metadata.tickers,
            }
        },
    )

    graph = build_graph()
    try:
        final_state: AgentState = await graph.ainvoke(state)
        trace.write(
            "run_end",
            run_id=metadata.run_id,
            total_cost_usd=final_state["metadata"].total_cost_usd,
            warnings=len(final_state["metadata"].warnings),
            errors=len(final_state["metadata"].errors),
        )
        save_checkpoint(metadata.run_id, final_state)
        return final_state
    except Exception as exc:
        trace.write("run_error", run_id=metadata.run_id, error=str(exc))
        save_checkpoint(metadata.run_id, state)
        raise


async def _run_single() -> None:
    await run_pipeline_once(
        trigger="manual",
        run_kind=RunKind.FULL_EXECUTION,
        execution_enabled=True,
        run_mode="single",
    )


async def _run_continuous() -> None:
    logger = get_logger("main")
    bus = EventBus()

    async def _handle_schedule(payload):
        decision = payload["decision"]
        await run_pipeline_once(
            trigger="schedule",
            run_kind=decision.run_kind,
            execution_enabled=decision.should_execute_orders,
            run_mode="continuous",
        )

    bus.subscribe("schedule", _handle_schedule)
    scheduler = ContinuousScheduler(event_bus=bus, event_name="schedule")
    logger.info(
        "continuous_scheduler_started",
        extra={"extra": {"tick_seconds": scheduler.tick_seconds, "event": "schedule"}},
    )
    await scheduler.run_forever()


async def _run_backtest() -> None:
    logger = get_logger("main")
    logger.info("backtest_mode_not_implemented")


def _resolve_run_mode(cli_mode: str | None) -> str:
    if cli_mode:
        return cli_mode
    return RUN_MODE


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trading agents entrypoint")
    parser.add_argument("--mode", choices=["single", "continuous", "backtest"], default=None)
    return parser.parse_args()


def main() -> None:
    validate_config()
    args = parse_args()
    run_mode = _resolve_run_mode(args.mode)
    if run_mode == "single":
        asyncio.run(_run_single())
        return
    if run_mode == "continuous":
        asyncio.run(_run_continuous())
        return
    if run_mode == "backtest":
        asyncio.run(_run_backtest())
        return
    raise ValueError(f"Unsupported run mode: {run_mode}")


if __name__ == "__main__":
    main()
