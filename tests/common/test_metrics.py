from __future__ import annotations

import pytest

from src.common.metrics import compute_metrics


def test_empty_dataset_returns_zero_metrics() -> None:
    metrics = compute_metrics([], [])
    assert metrics.total_trades == 0
    assert metrics.win_rate_pct == 0.0
    assert metrics.total_pnl_usdt == 0.0
    assert metrics.avg_rrr == 0.0
    assert metrics.max_drawdown_usdt == 0.0
    assert metrics.profit_factor == 0.0


def test_mixed_wins_losses_metrics() -> None:
    metrics = compute_metrics([20.0, -10.0, 30.0], [2.0, -1.0, 3.0])
    assert metrics.total_trades == 3
    assert metrics.win_rate_pct == pytest.approx(66.67, abs=0.01)
    assert metrics.total_pnl_usdt == 40.0
    assert metrics.avg_rrr == pytest.approx(1.3333, abs=0.0001)
    assert metrics.max_drawdown_usdt <= 0.0
    assert metrics.profit_factor == 5.0


def test_profit_factor_normalized_when_no_losses() -> None:
    metrics = compute_metrics([10.0, 20.0], [1.0, 2.0])
    assert metrics.total_trades == 2
    assert metrics.win_rate_pct == 100.0
    assert metrics.profit_factor == 0.0


def test_drawdown_sign_convention_is_non_positive() -> None:
    metrics = compute_metrics([10.0, 10.0, -30.0, 5.0], [1.0, 1.0, -3.0, 0.5])
    assert metrics.max_drawdown_usdt == pytest.approx(-30.0, abs=0.0001)
    assert metrics.max_drawdown_usdt <= 0.0
