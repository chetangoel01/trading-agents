# V1 Implementation Contract

This document locks the execution contract for the first production-quality paper-trading version of the system.

## Scope and Success

- First milestone: end-to-end paper trading MVP.
- Definition of done:
  - Stable daily automation on a schedule.
  - Complete run from ingestion to order fill.
  - Persistent traces and reports.
- Roadmap policy:
  - Follow the 5-week roadmap in `PLAN.md`.
  - Intra-phase task order can be adjusted for practicality.
- V1 scope includes all blueprint domains:
  - Dashboard, notifications, social, backtesting, feedback loop, and full strategy set.

## Trading and Strategy Policy

- Universe:
  - Fixed watchlist for v1 (default 5 mega-cap tickers in config).
  - Architecture remains extensible for a dynamic screener via new fetcher node.
- Asset policy:
  - Long-only equities.
  - Regular market hours execution only.
- Strategies:
  - All five active at launch.
  - Weight adjustments:
    - Manual review by default.
    - Auto-apply path implemented behind a config flag.
    - Auto-apply only at close (4:15 PM ET feedback run), never mid-session.

## Scheduling and Time

- Canonical timezone: `America/New_York`.
- Internal datetime representation: UTC.
- Scheduled runs (ET):
  - 9:00 AM: pre-market analysis-only (no execution).
  - Every 30 minutes, 9:30 AM through 3:30 PM: full pipeline with execution.
  - 4:15 PM: post-close feedback + daily summary (no execution).
- Midnight ET maintenance:
  - Daily trace cleanup for files older than 90 days.

## Run and Failure Semantics

- One run processes all configured tickers with a single `run_id`.
- Per-ticker fault isolation:
  - If model-dependent stage fails for one ticker, that ticker is forced to HOLD.
  - Other tickers continue normally in the same run.
- Non-LLM strategy signals can still be logged when LLM fails, but cannot execute trades.

## Risk and Capital Defaults

- Starting paper capital assumption: `$100,000`.
- Existing risk defaults in `config.py` are accepted.
- `MAX_DAILY_TRADES` remains global in v1.
- Kill switch behavior:
  - Halt new entries only.
  - No forced liquidation.
- Sector source:
  - Primary: Alpaca asset metadata.
  - Fallback: static `TICKER_SECTOR_MAP`.
  - If sector unknown:
    - Log warning.
    - Exclude from correlation-limit counting.

## Data Sources and Cost Policy

- Free-tier compatibility required.
- Social data:
  - Reddit required.
  - StockTwits optional if free access is available.
  - X/Twitter excluded.
- Transcript provider fallback:
  - No paid fallback in v1.
  - Degrade gracefully with warning if unavailable.
- LLM runtime budget policy:
  - Target < `$0.50` per full run.
  - Emit alert if any single run cost exceeds `$1.00`.

## Model Policy

- Role routing:
  - Extraction + sentiment: Qwen3-Coder.
  - Synthesis + decision + feedback: Claude Sonnet.
- Determinism:
  - Low temperature defaults.
  - Fixed seeds when API supports it.
- Safety fallback:
  - If both primary and fallback models fail, result is HOLD for that ticker.

## Execution Policy

- Entry type: market orders for v1.
- Bracket orders: required when supported by Alpaca.
- Scale-in trigger: time-based only (`SCALE_IN_INTERVAL_MINUTES`).
- Closed-market decisions:
  - Drop decisions (do not queue to next open).
- Partial fills:
  - Accept filled quantity.
  - Recompute stop/target against filled quantity.
  - Log unfilled remainder as cancelled.

## Persistence and Checkpointing

- Checkpointing:
  - Durable default: SQLite at `data/checkpoints.db`.
  - Redis can be used as acceleration layer when available.
  - Functionality cannot depend on Redis availability.
- Audit DB:
  - Canonical path: `data/trading.db`.
  - Persist outcomes and feedback for durable history.
- Prompt/response storage:
  - Full prompt/response retained in JSONL trace.
  - Queryable call metadata indexed in SQLite:
    - `run_id`, timestamp, model, role, ticker, tokens, cost, latency, success/failure.

## Trace Retention

- JSONL traces retained for 90 days.
- Cleanup runs daily at midnight ET.
- SQLite audit data retained indefinitely.

## Backtest Contract

- Baseline benchmark:
  - Year: 2025.
  - Tickers: v1 watchlist.
- Fill timing:
  - Configurable via `BACKTEST_FILL_TIMING`.
  - Allowed values: `next_bar_open`, `same_bar_close`.
  - Default: `next_bar_open`.
- Frictions:
  - Slippage: 0.05% on entry and exit.
  - Commission: $1 per order submission.
  - Round-trip typically totals two commissions (entry + exit leg).
- Gatekeeper metrics:
  - Sharpe > 1.0
  - Max drawdown < 20%
  - Win rate > 45%
- CI policy:
  - Unit tests in CI.
  - Backtests run manually or on a nightly schedule.

## Alerts and Deployment

- Day-one alerts:
  - Order fills
  - Stop-loss triggers
  - Kill switch activation
  - Critical pipeline errors
- Channels:
  - Slack primary
  - Email secondary
  - No SMS in v1
- Deployment:
  - Local Docker-first.
  - Portable to any Docker-capable machine.
- Observability baseline:
  - JSONL traces + trace viewer.
  - OpenTelemetry/Grafana deferred.

## Governance and Paper-to-Live Rule

- No additional compliance constraints for v1.
- Secrets in `.env`.
- Paper mode runs autonomously (no human approval gate).
- Live migration criteria (must be documented and met):
  - Sharpe > 1.0
  - 30+ days stable paper trading
  - Max drawdown < 15%
- Switch mechanism remains explicit manual config update (`ALPACA_BASE_URL`).
