# Trading Agents

Autonomous multi-agent paper-trading system built on LangGraph.

## Current Status

Initial repository scaffold is in place with locked v1 constraints in:

- `docs/V1_IMPLEMENTATION_CONTRACT.md`
- `config.py`

The source of truth architecture and full blueprint are documented in `PLAN.md`.

## Quick Start

1. Copy env template:
   - `cp .env.example .env`
2. Fill API keys in `.env`:
   - OpenRouter
   - Alpaca (paper)
   - Finnhub
   - Reddit
   - Slack webhook (optional but recommended)
3. Create virtual environment and install dependencies:
   - `python -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -r requirements.txt`
4. Bring up local services (Redis, app stack) once compose files are added in later phases.

## Design Constraints (Locked for V1)

- Canonical timezone: `America/New_York` (internal timestamps remain UTC).
- One run processes all watchlist tickers under one `run_id`.
- LLM failure is ticker-scoped: failed ticker degrades to HOLD, others proceed.
- Trade execution requires LLM-confirmed thesis/decision path.
- Checkpointing defaults to SQLite (`data/checkpoints.db`) with optional Redis acceleration.
- Audit DB is SQLite (`data/trading.db`) and retained indefinitely.
- JSONL trace retention is 90 days with scheduled cleanup.

## Backtest Defaults

- Fill timing default: `next_bar_open`
- Slippage: `0.05%` per leg
- Commission: `$1` per order submission

## Roadmap

Execution follows the week-by-week plan in `PLAN.md` with flexibility to reorder work within each phase.
