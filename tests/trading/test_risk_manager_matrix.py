from __future__ import annotations

from itertools import islice, product

import pytest

from src.strategy.signal_engine import Direction, Signal
from src.trading.risk_manager import PositionSize, RiskManager


def _signal(*, entry: float, stop: float, take_profit: float = 110.0) -> Signal:
    return Signal(
        symbol="BTCUSDT",
        timeframe="4h",
        direction=Direction.LONG,
        entry_price=entry,
        stop_loss=stop,
        take_profit=take_profit,
        fractal_ref=96.0,
    )


def _expected_allows_trade(
    *,
    entry: float,
    stop: float,
    available_balance: float,
    risk_pct: float,
    leverage: int,
    max_alloc_pct: float,
    min_notional: float,
    quantity_precision: int,
) -> bool:
    stop_distance = abs(entry - stop)
    if stop_distance == 0:
        return False

    risk_amount = available_balance * (risk_pct / 100.0)
    raw_qty = risk_amount / stop_distance
    notional = raw_qty * entry
    margin_required = notional / leverage
    max_allowed_margin = available_balance * (max_alloc_pct / 100.0)
    if margin_required > max_allowed_margin:
        return False

    qty = round(raw_qty, quantity_precision)
    if qty <= 0:
        return False

    if qty * entry < min_notional:
        return False

    return True


def _build_matrix_cases() -> list[tuple[float, float, float, float, int, float, float, int]]:
    stop_distances = [0.5, 1.0, 2.0, 5.0, 10.0]
    balances = [50.0, 100.0, 250.0, 500.0]
    risk_pcts = [0.1, 0.5, 1.0, 2.0]
    leverages = [1, 2, 5, 10, 20]
    max_allocs = [5.0, 10.0, 20.0, 30.0, 50.0, 100.0]
    min_notionals = [0.0, 5.0, 50.0]

    all_cases = product(
        stop_distances,
        balances,
        risk_pcts,
        leverages,
        max_allocs,
        min_notionals,
    )

    matrix = []
    for stop_distance, balance, risk_pct, leverage, max_alloc, min_notional in islice(
        all_cases,
        60,
    ):
        matrix.append(
            (
                100.0,
                100.0 - stop_distance,
                balance,
                risk_pct,
                leverage,
                max_alloc,
                min_notional,
                3,
            )
        )
    return matrix


MATRIX_CASES = _build_matrix_cases()


@pytest.mark.parametrize(
    (
        "entry",
        "stop",
        "available_balance",
        "risk_pct",
        "leverage",
        "max_alloc_pct",
        "min_notional",
        "quantity_precision",
    ),
    MATRIX_CASES,
)
def test_risk_manager_matrix_50_plus_scenarios(
    entry: float,
    stop: float,
    available_balance: float,
    risk_pct: float,
    leverage: int,
    max_alloc_pct: float,
    min_notional: float,
    quantity_precision: int,
) -> None:
    manager = RiskManager(
        risk_per_trade_pct=risk_pct,
        leverage=leverage,
        max_capital_allocation_pct=max_alloc_pct,
        min_notional=min_notional,
    )
    signal = _signal(entry=entry, stop=stop)

    pos = manager.calculate(
        signal,
        available_balance=available_balance,
        quantity_precision=quantity_precision,
    )

    expected = _expected_allows_trade(
        entry=entry,
        stop=stop,
        available_balance=available_balance,
        risk_pct=risk_pct,
        leverage=leverage,
        max_alloc_pct=max_alloc_pct,
        min_notional=min_notional,
        quantity_precision=quantity_precision,
    )

    assert pos.is_ok() is expected

    if pos.is_ok():
        position = pos.unwrap()
        assert isinstance(position, PositionSize)
        assert position.quantity > 0
        assert position.margin_required <= available_balance * (max_alloc_pct / 100.0) + 1e-9
        assert position.notional >= min_notional


def test_risk_manager_matrix_include_zero_stop_distance_case() -> None:
    manager = RiskManager(
        risk_per_trade_pct=1.0,
        leverage=10,
        max_capital_allocation_pct=100.0,
        min_notional=5.0,
    )
    signal = _signal(entry=100.0, stop=100.0)

    result = manager.calculate(signal, available_balance=1000.0, quantity_precision=3)
    assert result.is_err()
