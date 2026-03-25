# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A multi-agent autonomous paper-trading system built on LangGraph. Five parallel data fetchers feed into an LLM extraction → strategy → synthesis → decision → execution pipeline. Runs against Alpaca paper trading with OpenRouter-routed LLMs (Qwen3-Coder for extraction/sentiment, Claude Sonnet for synthesis/decision/feedback).

## Commands

```bash
# Install
pip install -e ".[dev]"

# Run
python main.py --mode single          # one-shot pipeline
python main.py --mode continuous       # scheduled loop (ET market hours)
python main.py --mode backtest         # backtest analysis only
python main.py --resume-run-id <id>    # resume from checkpoint

# Tests
pytest -q                              # all tests (runs from evals/ dir)
pytest evals/test_graph.py -q          # single test file
pytest evals/test_graph.py::test_name  # single test

# Dashboard
uvicorn dashboard.app:app --host 127.0.0.1 --port 8000
```

## Architecture

### Pipeline (graph.py)

```
START → [fetch_sec, fetch_news, fetch_transcripts, fetch_social, fetch_market_data] (parallel)
      → extract → strategize → synthesize → decide
      → route: has non-HOLD decisions? → execute → monitor → feedback → format → END
                                   no? → feedback → format → END
```

### Shared State (state.py)

All agents read/write a single `AgentState` TypedDict with Pydantic models and LangGraph reducers. List channels use `operator.add` for parallel merge safety. Key models: `RawDocument`, `ExtractedSignal`, `StrategySignal`, `TickerThesis`, `TradeDecision`, `OrderRecord`, `PortfolioSnapshot`, `FeedbackState`, `RunMetadata`.

### Model Routing (config.py → ModelRole)

| Role | Model | Use |
|------|-------|-----|
| EXTRACTION | qwen/qwen3-coder | Parse raw docs into structured signals |
| SYNTHESIS | claude-sonnet | Generate bull/bear theses |
| DECISION | claude-sonnet | Final trade decisions |
| SENTIMENT | qwen/qwen3-coder | Sentiment scoring |
| FEEDBACK | claude-sonnet | Outcome analysis |

Each role has fallback models configured in `MODEL_FALLBACKS`.

### Strategy Weights (config.py)

fundamental(0.35), momentum(0.20), event_driven(0.20), sentiment(0.15), mean_reversion(0.10)

### Risk Controls (config.py)

Hardcoded guardrails — not LLM-overridable: MIN_CONFIDENCE=0.65, MAX_POSITION_PCT=0.10, STOP_LOSS_PCT=-0.05, MAX_DRAWDOWN_PCT=-0.15, MAX_DAILY_TRADES=20.

### Persistence

- `data/checkpoints.db` — SQLite, resumable pipeline state
- `data/trading.db` — SQLite audit DB, run history + LLM call metadata
- `traces/<run_id>.jsonl` — execution traces, 90-day retention
- Optional Redis cache layer

### Scheduling (scheduler.py)

ET-based windows: 9:00 premarket analysis, 9:30-15:30 every 30min execution, 4:15 postclose feedback. Continuous mode ticks every 30 seconds.

## Key Design Decisions

- **Per-ticker fault isolation**: If LLM extraction fails for one ticker, it falls back to HOLD — other tickers continue normally.
- **Parallel fetch fan-out**: `project_parallel_fetch_update()` in graph.py returns only reducer-safe channels to avoid merge conflicts.
- **Long-only equities, regular hours only** (V1 constraint).
- **One run = all tickers** in the watchlist processed together.
- **Tests use pytest-asyncio with `asyncio_mode = auto`** — async test functions don't need `@pytest.mark.asyncio`.

## Environment Variables

Copy `.env.example` to `.env`. Required: `OPENROUTER_API_KEY`, `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `FINNHUB_API_KEY`, `SEC_USER_AGENT`, `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`.
