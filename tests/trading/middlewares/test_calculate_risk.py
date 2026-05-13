from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.strategy.signal_engine import SignalResult
from src.trading.middlewares.calculate_risk import CalculateRiskMiddleware
from src.trading.tick_pipeline import TickContext


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.fetch_usdt_balance = AsyncMock(return_value=1000.0)
    client.get_quantity_precision = MagicMock(return_value=3)
    return client


@pytest.fixture
def mock_risk_manager():
    rm = MagicMock()
    position = MagicMock()
    position.symbol = "BTCUSDT"
    position.quantity = 0.1
    rm.calculate = MagicMock(return_value=position)
    rm.consume_last_rejection = MagicMock(return_value=None)
    return rm


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.get_intraday_realized_pnl_usdt = AsyncMock(return_value=0.0)
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
    return ctx


class TestCalculateRiskMiddleware:
    async def test_calculate_risk_success(
        self, mock_client, mock_risk_manager, mock_repo, tick_context
    ):
        middleware = CalculateRiskMiddleware(mock_client, mock_risk_manager, mock_repo)
        next_called = False

        async def next():
            nonlocal next_called
            next_called = True

        await middleware.process(tick_context, next)

        assert not tick_context.aborted
        assert tick_context.position is not None
        assert next_called

    async def test_zero_balance(self, mock_client, mock_risk_manager, mock_repo, tick_context):
        mock_client.fetch_usdt_balance = AsyncMock(return_value=0.0)
        middleware = CalculateRiskMiddleware(mock_client, mock_risk_manager, mock_repo)
        next_called = False

        async def next():
            nonlocal next_called
            next_called = True

        await middleware.process(tick_context, next)

        assert tick_context.aborted
        assert "zero_or_negative_balance" in tick_context.abort_reason
        assert not next_called

    async def test_position_rejected(self, mock_client, mock_risk_manager, mock_repo, tick_context):
        mock_risk_manager.calculate = MagicMock(return_value=None)
        rejection = MagicMock()
        rejection.reason = "MAX_CAPITAL_ALLOCATION_EXCEEDED"
        mock_risk_manager.consume_last_rejection = MagicMock(return_value=rejection)
        middleware = CalculateRiskMiddleware(mock_client, mock_risk_manager, mock_repo)
        next_called = False

        async def next():
            nonlocal next_called
            next_called = True

        await middleware.process(tick_context, next)

        assert tick_context.aborted
        assert "position_size_rejected" in tick_context.abort_reason
        assert not next_called
