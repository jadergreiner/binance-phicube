from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.trading.middlewares.notify import NotifyMiddleware
from src.trading.order_manager import TradeStatus
from src.trading.tick_pipeline import TickContext


@pytest.fixture
def mock_notifier():
    notifier = MagicMock()
    notifier.send = AsyncMock()
    return notifier


@pytest.fixture
def tick_context():
    return TickContext(symbol="BTCUSDT", timeframe="15m")


class TestNotifyMiddleware:
    async def test_notify_trade_opened(self, mock_notifier, tick_context):
        trade = MagicMock()
        trade.status = TradeStatus.OPEN
        trade.symbol = "BTCUSDT"
        trade.direction = "LONG"
        trade.quantity = 0.1
        trade.entry_price = 50000.0
        trade.stop_loss = 49000.0
        trade.take_profit = 52000.0
        trade.risk_amount = 100.0
        trade.opened_at = "2024-01-01T00:00:00"
        tick_context.trade = trade

        middleware = NotifyMiddleware(mock_notifier)
        next_called = False

        async def next():
            nonlocal next_called
            next_called = True

        await middleware.process(tick_context, next)

        mock_notifier.send.assert_called_once()
        assert next_called

    async def test_notify_no_trade(self, mock_notifier, tick_context):
        middleware = NotifyMiddleware(mock_notifier)
        next_called = False

        async def next():
            nonlocal next_called
            next_called = True

        await middleware.process(tick_context, next)

        mock_notifier.send.assert_not_called()
        assert next_called
