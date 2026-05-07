from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from src.strategy.signal_engine import Direction, Signal
from src.trading.order_manager import OrderManager, TradeStatus
from src.trading.risk_manager import PositionSize


def _sample_signal() -> Signal:
    return Signal(
        symbol="BTCUSDT",
        timeframe="4h",
        direction=Direction.LONG,
        entry_price=50000.0,
        stop_loss=49000.0,
        take_profit=52000.0,
        fractal_ref=48500.0,
        detected_at=datetime.now(UTC),
    )


def _sample_position() -> PositionSize:
    return PositionSize(
        symbol="BTCUSDT",
        direction=Direction.LONG,
        quantity=0.001,
        notional=50.0,
        margin_required=25.0,
        entry_price=50000.0,
        stop_loss=49000.0,
        take_profit=52000.0,
        risk_amount=10.0,
    )


def _mock_client() -> AsyncMock:
    client = AsyncMock()
    client.set_leverage = AsyncMock()
    client.set_margin_mode = AsyncMock()
    client.create_market_order = AsyncMock(return_value={"id": "entry-1", "average": "50000.0"})
    client.round_price = AsyncMock(side_effect=[49000.0, 52000.0])
    client.create_stop_loss_order = AsyncMock(return_value={"id": "sl-1"})
    client.create_take_profit_order = AsyncMock(return_value={"id": "tp-1"})
    client.cancel_all_orders = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_execute_rolls_back_when_stop_loss_creation_fails() -> None:
    client = _mock_client()
    client.create_stop_loss_order.side_effect = Exception("SL failed")
    notifier = AsyncMock()
    manager = OrderManager(client=client, leverage=5, notifier=notifier)

    trade = await manager.execute(_sample_signal(), _sample_position())

    assert trade is not None
    assert trade.status == TradeStatus.FAILED
    client.cancel_all_orders.assert_called_once_with("BTCUSDT")
    notifier.send.assert_called_once()


@pytest.mark.asyncio
async def test_execute_rolls_back_when_take_profit_creation_fails() -> None:
    client = _mock_client()
    client.create_take_profit_order.side_effect = Exception("TP failed")
    manager = OrderManager(client=client, leverage=5, notifier=None)

    trade = await manager.execute(_sample_signal(), _sample_position())

    assert trade is not None
    assert trade.status == TradeStatus.FAILED
    client.cancel_all_orders.assert_called_once_with("BTCUSDT")

