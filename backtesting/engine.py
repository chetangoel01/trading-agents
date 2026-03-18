from __future__ import annotations

from dataclasses import dataclass

from config import BACKTEST_COMMISSION_USD_PER_ORDER, BACKTEST_SLIPPAGE_PCT_PER_LEG
from backtesting.metrics import max_drawdown_pct, sharpe_ratio, win_rate


@dataclass(frozen=True)
class PriceBar:
    ts: str
    open: float
    close: float


def _apply_buy_slippage(price: float) -> float:
    return price * (1 + BACKTEST_SLIPPAGE_PCT_PER_LEG)


def _apply_sell_slippage(price: float) -> float:
    return price * (1 - BACKTEST_SLIPPAGE_PCT_PER_LEG)


def run_backtest(
    *,
    bars: list[PriceBar],
    entry_signal_indices: list[int],
    exit_signal_indices: list[int],
    initial_cash: float,
    quantity: int,
) -> dict:
    if not bars:
        return {"trades": [], "metrics": {"sharpe_ratio": 0.0, "max_drawdown_pct": 0.0, "win_rate": 0.0}}

    cash = initial_cash
    trades: list[dict] = []
    equity_curve: list[float] = [cash]

    for entry_idx, exit_idx in zip(entry_signal_indices, exit_signal_indices, strict=False):
        if entry_idx + 1 >= len(bars) or exit_idx + 1 >= len(bars):
            continue
        entry_fill_idx = entry_idx + 1
        exit_fill_idx = exit_idx + 1
        entry_fill_price = _apply_buy_slippage(bars[entry_fill_idx].open)
        exit_fill_price = _apply_sell_slippage(bars[exit_fill_idx].open)
        gross_pnl = (exit_fill_price - entry_fill_price) * quantity
        commission_total = BACKTEST_COMMISSION_USD_PER_ORDER * 2
        net_pnl = gross_pnl - commission_total
        cash += net_pnl
        equity_curve.append(cash)
        trades.append(
            {
                "entry_signal_index": entry_idx,
                "entry_fill_index": entry_fill_idx,
                "entry_fill_price": entry_fill_price,
                "exit_signal_index": exit_idx,
                "exit_fill_index": exit_fill_idx,
                "exit_fill_price": exit_fill_price,
                "commission_total_usd": commission_total,
                "net_pnl_usd": net_pnl,
            }
        )

    returns: list[float] = []
    for idx in range(1, len(equity_curve)):
        prev = equity_curve[idx - 1]
        curr = equity_curve[idx]
        if prev != 0:
            returns.append((curr - prev) / prev)

    outcomes = [trade["net_pnl_usd"] for trade in trades]
    metrics = {
        "sharpe_ratio": sharpe_ratio(returns),
        "max_drawdown_pct": max_drawdown_pct(equity_curve),
        "win_rate": win_rate(outcomes),
    }
    return {"trades": trades, "metrics": metrics, "equity_curve": equity_curve}
