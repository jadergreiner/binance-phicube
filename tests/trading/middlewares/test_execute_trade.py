from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.strategy.signal_engine import SignalResult
from src.trading.middlewares.execute_trade import ExecuteTradeMiddleware
from src.trading.order_manager import TradeStatus
from src.trading.tick_pipeline import TickContext


@pytest.fixture
def mock_order_manager():
    om = MagicMock()
    trade = MagicMock()
    trade.symbol = "BTCUSDT"
    trade.status = TradeStatus.OPEN
    trade.to_dict = MagicMock(return_value={"symbol": "BTCUSDT"})
    om.execute = AsyncMock(return_value=trade)
    return om


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.save_trade = AsyncMock(return_value="trade_123")
    repo.audit = AsyncMock()
    return repo


@pytest.fixture
def tick_context():
    ctx = TickContext(symbol="BTCUSDT", timeframe="15m")
    ctx.signal = SignalResult(
        direction="LONG",
        entry_price=50000.0,
        stop_loss=49000.0,
        take_profit=52000.0,
    )
    ctx.position = MagicMock()
    return ctx


class TestExecuteTradeMiddleware:
    async def test_execute_trade_success(self, mock_order_manager, mock_repo, tick_context):
        middleware = ExecuteTradeMiddleware(mock_order_manager, mock_repo)
        next_called = False

        async def next():
            nonlocal next_called
            next_called = True

        await middleware.process(tick_context, next)

        assert not tick_context.aborted
        assert tick_context.trade is not None
        assert tick_context.metrics["trade_id"] == "trade_123"
        assert next_called

    async def test_execute_trade_none(self, mock_order_manager, mock_repo, tick_context):
        mock_order_manager.execute = AsyncMock(return_value=None)
        middleware = ExecuteTradeMiddleware(mock_order_manager, mock_repo)
        next_called = False

        async def next():
            nonlocal next_called
            next_called = True

        await middleware.process(tick_context, next)

        assert tick_context.aborted
        assert "order_manager_execute_returned_none" in tick_context.abort_reason
        assert not next_called
