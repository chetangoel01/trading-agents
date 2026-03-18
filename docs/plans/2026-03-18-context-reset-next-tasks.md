# Context Reset Next Tasks (2026-03-18)

Purpose: allow a clean-session resume without re-discovering state.

## Current State

- Branch: `master`
- Test command: `.venv/bin/pytest -q`
- Current result: `37 passed`
- Untracked by design: `PLAN.md`

## Commit Trail (Chronological)

1. `f61c3c0` Initialize project foundation with locked v1 contract.
2. `eb61611` Add initial SEC/news fetchers and graph decision routing.
3. `5ee6a0e` Add run orchestration, tracing, and checkpointed entrypoint.
4. `84f1b5e` Implement decision risk gates and position sizing engine.
5. `0f5273a` Implement execution window gating and simulated fill handling.
6. `bae662d` Add monitor-driven exits and feedback calibration baseline.

## What Is Implemented

- Typed state schema and configuration invariants.
- Mode-aware entrypoint (`single`, `continuous`, `backtest` stub).
- JSONL run tracing and SQLite checkpoints/audit skeleton.
- SEC/news fetchers with parsing helpers, dedupe, and cache integration.
- Decision engine risk gates and sizing.
- Execution rules for non-execution windows, market-closed drops, and partial-fill bookkeeping.
- Monitor agent stop/take-profit/trailing-stop exits.
- Feedback agent baseline outcomes + calibration/performance summaries.

## Highest-Priority Next Tasks (From PLAN.md)

### 1) Complete remaining fetchers and technical data

- Implement `agents/fetchers/transcript.py` with graceful no-transcript behavior.
- Implement `agents/fetchers/social.py` for Reddit-first sentiment ingestion.
- Implement `agents/fetchers/market_data.py` for OHLCV + indicator computation.
- Add fixture-driven tests for each fetcher.

### 2) Implement extraction + synthesis with LLM routing

- Build extraction prompt path and structured parsing in `agents/extraction.py`.
- Build synthesis prompt path and thesis generation in `agents/synthesis.py`.
- Ensure per-ticker failure isolation (`HOLD` on failed ticker, continue others).
- Persist LLM call metadata to SQLite index and full prompt/response to trace.

### 3) Finish graph fan-out/fan-in shape

- Replace current sequential fetch chain with true parallel fetch fan-out + reducer-compatible state behavior.
- Keep single `run_id` across all tickers.

### 4) Scheduler/event integration

- Wire `events/bus.py` into `scheduler.py` + `main.py`.
- Enforce ET windows:
  - 9:00 analysis-only
  - 9:30-15:30 full execution every 30 min
  - 16:15 feedback-only
  - midnight trace cleanup

### 5) Persistence hardening

- Add explicit checkpoint reload/resume path.
- Expand SQLite schema for run-level indexing/query.

### 6) Dashboard + notifications foundation

- Add FastAPI endpoints for portfolio/runs/strategies.
- Add Slack + email notifier stubs and tests.

## Resume Commands

```bash
source .venv/bin/activate
git status --short
.venv/bin/pytest -q
```

Then proceed with Task 1 (remaining fetchers) using TDD-first cycles.
