from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.trading.middlewares.validate_limits import ValidateLimitsMiddleware
from src.trading.tick_pipeline import TickContext


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.count_open_trades = AsyncMock(return_value=0)
    repo.get_open_trades_for_symbol = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def tick_context():
    return TickContext(symbol="BTCUSDT", timeframe="15m")


class TestValidateLimitsMiddleware:
    async def test_validate_limits_success(self, mock_repo, tick_context):
        middleware = ValidateLimitsMiddleware(mock_repo, max_open_positions=3)
        next_called = False

        async def next():
            nonlocal next_called
            next_called = True

        await middleware.process(tick_context, next)

        assert not tick_context.aborted
        assert next_called

    async def test_validate_limits_max_positions_reached(self, mock_repo, tick_context):
        mock_repo.count_open_trades = AsyncMock(return_value=3)
        middleware = ValidateLimitsMiddleware(mock_repo, max_open_positions=3)
        next_called = False

        async def next():
            nonlocal next_called
            next_called = True

        await middleware.process(tick_context, next)

        assert tick_context.aborted
        assert "max_positions_reached" in tick_context.abort_reason
        assert not next_called

    async def test_validate_limits_symbol_already_in_trade(self, mock_repo, tick_context):
        mock_repo.get_open_trades_for_symbol = AsyncMock(return_value=[{"symbol": "BTCUSDT"}])
        middleware = ValidateLimitsMiddleware(mock_repo, max_open_positions=3)
        next_called = False

        async def next():
            nonlocal next_called
            next_called = True

        await middleware.process(tick_context, next)

        assert tick_context.aborted
        assert "symbol_already_in_trade" in tick_context.abort_reason
        assert not next_called
