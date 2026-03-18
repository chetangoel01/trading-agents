from __future__ import annotations

from backtesting.engine import PriceBar, run_backtest


def test_backtest_uses_next_bar_open_fill_timing() -> None:
    bars = [
        PriceBar(ts="2025-01-01", open=100.0, close=101.0),
        PriceBar(ts="2025-01-02", open=102.0, close=103.0),
        PriceBar(ts="2025-01-03", open=104.0, close=105.0),
    ]
    result = run_backtest(
        bars=bars,
        entry_signal_indices=[0],
        exit_signal_indices=[1],
        initial_cash=100000.0,
        quantity=10,
    )
    trade = result["trades"][0]
    assert trade["entry_signal_index"] == 0
    assert trade["entry_fill_index"] == 1
    assert trade["exit_signal_index"] == 1
    assert trade["exit_fill_index"] == 2


def test_backtest_applies_slippage_and_commission() -> None:
    bars = [
        PriceBar(ts="2025-01-01", open=100.0, close=100.0),
        PriceBar(ts="2025-01-02", open=100.0, close=100.0),
        PriceBar(ts="2025-01-03", open=100.0, close=100.0),
    ]
    result = run_backtest(
        bars=bars,
        entry_signal_indices=[0],
        exit_signal_indices=[1],
        initial_cash=100000.0,
        quantity=10,
    )
    trade = result["trades"][0]
    assert trade["entry_fill_price"] > 100.0
    assert trade["exit_fill_price"] < 100.0
    assert trade["commission_total_usd"] == 2.0
    assert trade["net_pnl_usd"] < 0.0


def test_backtest_outputs_baseline_metrics() -> None:
    bars = [
        PriceBar(ts="2025-01-01", open=100.0, close=101.0),
        PriceBar(ts="2025-01-02", open=102.0, close=102.0),
        PriceBar(ts="2025-01-03", open=103.0, close=103.0),
        PriceBar(ts="2025-01-04", open=104.0, close=104.0),
    ]
    result = run_backtest(
        bars=bars,
        entry_signal_indices=[0],
        exit_signal_indices=[2],
        initial_cash=100000.0,
        quantity=10,
    )
    metrics = result["metrics"]
    assert "sharpe_ratio" in metrics
    assert "max_drawdown_pct" in metrics
    assert "win_rate" in metrics
