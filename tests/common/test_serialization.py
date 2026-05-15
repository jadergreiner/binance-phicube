from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from src.common.serialization import (
    auto_dict,
    clear_adapters,
    register_adapter,
    set_sensitive_policy,
)
from src.strategy.signal_engine import Direction, Signal
from src.trading.order_manager import Trade, TradeStatus
from src.trading.risk_manager import PositionSize


@dataclass
class _LegacyType:
    value: int


@auto_dict
@dataclass
class _Nested:
    amount: int


@auto_dict
@dataclass
class _Container:
    nested: _Nested
    items: list[_Nested]
    legacy: _LegacyType | None = None
    api_key: str | None = None


def test_auto_dict_rejects_non_dataclass() -> None:
    class _NotDataclass:
        pass

    with pytest.raises(TypeError):
        auto_dict(_NotDataclass)


def test_recursive_and_list_serialization() -> None:
    set_sensitive_policy("omit")
    obj = _Container(nested=_Nested(10), items=[_Nested(1), _Nested(2)], api_key="secret")
    data = obj.to_dict()
    assert data["nested"] == {"amount": 10}
    assert data["items"] == [{"amount": 1}, {"amount": 2}]
    assert "api_key" not in data


def test_sensitive_policy_switch_mask_vs_omit() -> None:
    obj = _Container(nested=_Nested(10), items=[], api_key="secret")

    set_sensitive_policy("omit")
    omitted = obj.to_dict()
    assert "api_key" not in omitted

    set_sensitive_policy("mask")
    masked = obj.to_dict()
    assert masked["api_key"] == "***"

    set_sensitive_policy("omit")


def test_adapter_based_serialization() -> None:
    clear_adapters()
    register_adapter(_LegacyType, lambda legacy: {"legacy_value": legacy.value})
    obj = _Container(nested=_Nested(10), items=[], legacy=_LegacyType(7))
    data = obj.to_dict()
    assert data["legacy"] == {"legacy_value": 7}
    clear_adapters()


def test_datetime_format_compatibility_is_preserved() -> None:
    fixed_dt = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    trade = Trade(
        symbol="BTCUSDT",
        timeframe="15m",
        direction=Direction.LONG,
        quantity=0.1,
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        risk_amount=10.0,
        margin_used=5.0,
        entry_order_id="e1",
        status=TradeStatus.OPEN,
        opened_at=fixed_dt,
    )
    data = trade.to_dict()
    assert data["opened_at"] is fixed_dt


def test_cyclic_reference_fails_deterministically() -> None:
    @auto_dict
    @dataclass
    class _Node:
        name: str
        next: _Node | None = None

    a = _Node("a")
    b = _Node("b")
    a.next = b
    b.next = a

    with pytest.raises(ValueError, match="cyclic_reference_detected"):
        a.to_dict()


def test_position_size_parity_keys_and_values() -> None:
    pos = PositionSize(
        symbol="BTCUSDT",
        direction=Direction.SHORT,
        quantity=0.2,
        notional=20.0,
        margin_required=4.0,
        entry_price=100.0,
        stop_loss=105.0,
        take_profit=90.0,
        risk_amount=1.0,
    )
    data = pos.to_dict()
    assert data["direction"] == "SHORT"
    assert data["quantity"] == 0.2
    assert data["risk_amount"] == 1.0


def test_trade_parity_with_optional_none_fields() -> None:
    trade = Trade(
        symbol="BTCUSDT",
        timeframe="15m",
        direction=Direction.LONG,
        quantity=0.1,
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        risk_amount=10.0,
        margin_used=5.0,
        entry_order_id="e1",
        status=TradeStatus.OPEN,
    )
    data = trade.to_dict()
    assert data["direction"] == "LONG"
    assert data["status"] == "OPEN"
    assert "pnl" in data
    assert data["pnl"] is None
    assert "exit_strategy" in data
    assert data["exit_strategy"] is None


def test_signal_manual_serializer_is_preserved() -> None:
    signal = Signal(
        symbol="BTCUSDT",
        timeframe="15m",
        direction=Direction.LONG,
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        fractal_ref=98.0,
    )
    data = signal.to_dict()
    assert "risk_reward_ratio" in data
    assert data["direction"] == "LONG"
