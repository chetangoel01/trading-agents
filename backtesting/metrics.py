from __future__ import annotations

import math


def sharpe_ratio(returns: list[float], risk_free_rate: float = 0.0) -> float:
    if not returns:
        return 0.0
    excess = [r - risk_free_rate for r in returns]
    mean = sum(excess) / len(excess)
    variance = sum((x - mean) ** 2 for x in excess) / len(excess)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return mean / std


def max_drawdown_pct(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        if peak > 0:
            drawdown = (peak - value) / peak
            if drawdown > max_dd:
                max_dd = drawdown
    return max_dd


def win_rate(outcomes: list[float]) -> float:
    if not outcomes:
        return 0.0
    wins = sum(1 for x in outcomes if x > 0)
    return wins / len(outcomes)
