"""CLI entrypoint for single/continuous/backtest modes."""

from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
from datetime import UTC, datetime
import uuid

from backtesting.engine import PriceBar, run_backtest
from config import RUN_MODE, STARTING_PAPER_CAPITAL_USD, WATCHLIST, validate_config
from events.bus import EventBus
from graph import build_graph
from scheduler import ContinuousScheduler, RunKind
from state import AgentState, FeedbackState, PortfolioSnapshot, RunMetadata
from utils.audit_store import finalize_run_record, insert_run_record_start
from utils.checkpoint_store import hydrate_state, load_checkpoint, save_checkpoint
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

    insert_run_record_start(
        run_id=metadata.run_id,
        started_at=metadata.started_at,
        trigger=trigger,
        run_mode=run_mode,
        run_kind=metadata.schedule_run_kind,
        execution_enabled=execution_enabled,
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
        finalize_run_record(
            run_id=metadata.run_id,
            status="completed",
            warnings_count=len(final_state["metadata"].warnings),
            errors_count=len(final_state["metadata"].errors),
            total_cost_usd=final_state["metadata"].total_cost_usd,
        )
        return final_state
    except Exception as exc:
        trace.write("run_error", run_id=metadata.run_id, error=str(exc))
        save_checkpoint(metadata.run_id, state)
        finalize_run_record(
            run_id=metadata.run_id,
            status="failed",
            warnings_count=len(state["metadata"].warnings),
            errors_count=len(state["metadata"].errors) + 1,
            total_cost_usd=state["metadata"].total_cost_usd,
        )
        raise


async def _run_single() -> None:
    await run_pipeline_once(
        trigger="manual",
        run_kind=RunKind.FULL_EXECUTION,
        execution_enabled=True,
        run_mode="single",
    )


async def _run_resume(run_id: str) -> None:
    logger = get_logger("main")
    raw_state = load_checkpoint(run_id)
    if raw_state is None:
        raise ValueError(f"No checkpoint found for run_id={run_id}")
    state = hydrate_state(raw_state)
    logger.info("resume_start", extra={"extra": {"run_id": run_id}})
    graph = build_graph()
    final_state: AgentState = await graph.ainvoke(state)
    save_checkpoint(run_id, final_state)


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
    # Run pipeline in backtest mode (no real execution)
    state = await run_pipeline_once(
        trigger="backtest",
        run_kind=None,
        execution_enabled=False,
        run_mode="backtest",
    )

    tech_data = state["technical_data"]
    if not tech_data:
        logger.warning("backtest_no_technical_data")
        return

    by_ticker: dict[str, list] = defaultdict(list)
    for snap in tech_data:
        by_ticker[snap.ticker].append(snap)

    for ticker, snapshots in by_ticker.items():
        snapshots.sort(key=lambda s: s.timestamp)
        bars = [PriceBar(ts=str(s.timestamp), open=s.price, close=s.price) for s in snapshots]
        if len(bars) < 2:
            continue

        buy_decisions = [d for d in state["decisions"] if d.ticker == ticker and d.action.value == "buy"]
        entry_indices = [0] if buy_decisions else []
        exit_indices = [len(bars) - 2] if entry_indices else []

        result = run_backtest(
            bars=bars,
            entry_signal_indices=entry_indices,
            exit_signal_indices=exit_indices,
            initial_cash=STARTING_PAPER_CAPITAL_USD,
            quantity=100,
        )
        logger.info(
            "backtest_result",
            extra={"extra": {"ticker": ticker, "metrics": result["metrics"], "trades": len(result["trades"])}},
        )


def _resolve_run_mode(cli_mode: str | None) -> str:
    if cli_mode:
        return cli_mode
    return RUN_MODE


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trading agents entrypoint")
    parser.add_argument("--mode", choices=["single", "continuous", "backtest"], default=None)
    parser.add_argument("--resume-run-id", default=None)
    return parser.parse_args()


def main() -> None:
    validate_config()
    args = parse_args()
    if args.resume_run_id:
        asyncio.run(_run_resume(args.resume_run_id))
        return
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
