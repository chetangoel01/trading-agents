from __future__ import annotations

import pytest

import config


def test_strategy_weights_sum_to_one() -> None:
    # This asserts our locked v1 invariant.
    config.validate_config()


def test_backtest_fill_timing_must_be_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "BACKTEST_FILL_TIMING", "invalid_mode")
    with pytest.raises(ValueError):
        config.validate_config()
