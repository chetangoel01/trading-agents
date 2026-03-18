# Next Chat Handoff (2026-03-18)

Use this file to resume implementation in a fresh chat without re-discovery.

## Current Baseline

- Branch: `master`
- Test command: `.venv/bin/pytest -q`
- Latest observed status: `48 passed, 1 warning`
- Known intentional untracked file: `PLAN.md`

## Recent Milestones (Already Done)

- Foundation scaffold, config contract, typed state, and scheduler windows.
- Fetchers implemented:
  - SEC
  - News
  - Transcripts
  - Social (Reddit-first)
  - Market data + technical indicators
- Core agents implemented:
  - Extraction (LLM-backed + ticker-scoped failure isolation)
  - Synthesis (LLM-backed + neutral fallback per failed ticker)
  - Decision (risk gates + sizing)
  - Execution (market-hours/drop behavior + partial fill bookkeeping)
  - Monitor (stop-loss/take-profit/trailing-stop exits)
  - Feedback (outcome recording + calibration/performance summaries)
- Graph now uses parallel fetch fan-out/fan-in with reducer-aware state fields.
- Continuous scheduler dispatches through event bus.
- Checkpoint resume path added via `--resume-run-id` with typed state hydration.

## Immediate Next Steps (Priority Order)

### 1) Dashboard/API Foundation

- Implement `dashboard/app.py` FastAPI app with:
  - `GET /api/portfolio`
  - `GET /api/runs`
  - `GET /api/strategies`
- Source data from checkpoint/audit persistence layer for now.
- Add tests for response shape and status codes.

### 2) Notifications Foundation

- Implement notifier stubs:
  - `notifications/slack.py`
  - `notifications/email.py`
- Wire triggers for:
  - order fills
  - stop-loss events
  - kill-switch warning
  - critical pipeline errors
- Add unit tests for payload formatting and trigger routing.

### 3) Formatter Agent Output Contract

- Implement `agents/formatter.py` to produce:
  - `state.formatted_report` text report
  - compact dashboard payload emission
- Include run metadata, signal counts, decisions, orders, portfolio, feedback, warnings/errors.
- Add tests for required sections and non-empty report generation.

### 4) Persistence Expansion (Run Indexes)

- Add run-level table(s) in SQLite for:
  - run_id
  - started_at
  - trigger
  - run_kind
  - execution_enabled
  - status / warnings / errors counts
  - total_cost_usd
- Write records at run start/end for easier dashboard queries.

### 5) Backtesting Engine Skeleton

- Add `backtesting/engine.py` + `backtesting/metrics.py` baseline.
- Implement:
  - date loop
  - next-bar-open fill default
  - slippage/commission application
  - metric outputs (Sharpe, drawdown, win rate)
- Keep deterministic and fixture-driven initially.

## Resume Commands

```bash
source .venv/bin/activate
git status --short
.venv/bin/pytest -q
```

Then start with **Dashboard/API Foundation** in TDD cycles and commit each slice atomically.
