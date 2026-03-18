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
4. Run tests:
   - `.venv/bin/pytest -q`

## Running the System

### Pipeline modes (`main.py`)

- Single run:
  - `.venv/bin/python main.py --mode single`
- Continuous scheduler mode:
  - `.venv/bin/python main.py --mode continuous`
- Resume from checkpointed run:
  - `.venv/bin/python main.py --resume-run-id <run_id>`
- Backtest mode entrypoint (stub):
  - `.venv/bin/python main.py --mode backtest`

Data written by runs:
- Checkpoints: `data/checkpoints.db`
- Audit/run indexes: `data/trading.db`
- Traces: `traces/<run_id>.jsonl`

### Dashboard API + UI

Start server:
- `.venv/bin/uvicorn dashboard.app:app --host 127.0.0.1 --port 8000 --reload`

Open dashboard:
- [http://127.0.0.1:8000](http://127.0.0.1:8000)

Core API endpoints:
- `GET /api/portfolio`
- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/trace`
- `GET /api/strategies`
- `GET /api/outcomes`

Note: if API responses are empty, run the pipeline once in `single` mode first so checkpoint/audit data exists.

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
