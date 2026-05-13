"""Testes para CreateStopLossCommand."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.config.settings import ExitStrategy
from src.trading.commands.stop_loss import CreateStopLossCommand


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.round_price = MagicMock(side_effect=lambda s, p: round(p, 2))
    client.create_stop_loss_order = AsyncMock(
        return_value={
            "id": "sl_123",
            "status": "open",
        }
    )
    client.create_trailing_stop_order = AsyncMock(
        return_value={
            "id": "ts_123",
            "status": "open",
        }
    )
    client.cancel_all_orders = AsyncMock(return_value=None)
    return client


class TestCreateStopLossCommand:
    async def test_execute_fixed_sl_success(self, mock_client):
        cmd = CreateStopLossCommand(
            client=mock_client,
            symbol="BTCUSDT",
            side="sell",
            quantity=0.1,
            stop_price=49000.0,
            exit_strategy=ExitStrategy.FIXED,
        )
        result = await cmd.execute()

        assert result["id"] == "sl_123"
        assert cmd.executed is True
        mock_client.create_stop_loss_order.assert_awaited_once()
        mock_client.create_trailing_stop_order.assert_not_awaited()

    async def test_execute_trailing_stop_success(self, mock_client):
        cmd = CreateStopLossCommand(
            client=mock_client,
            symbol="BTCUSDT",
            side="sell",
            quantity=0.1,
            stop_price=49000.0,
            exit_strategy=ExitStrategy.TRAILING,
            trailing_activation_pct=1.0,
            trailing_callback_rate=0.5,
            entry_price=50000.0,
        )
        result = await cmd.execute()

        assert result["id"] == "ts_123"
        assert cmd.executed is True
        mock_client.create_trailing_stop_order.assert_awaited_once()
        mock_client.create_stop_loss_order.assert_not_awaited()

    async def test_execute_failure(self, mock_client):
        mock_client.create_stop_loss_order = AsyncMock(side_effect=Exception("SL creation failed"))
        cmd = CreateStopLossCommand(
            client=mock_client,
            symbol="BTCUSDT",
            side="sell",
            quantity=0.1,
            stop_price=49000.0,
        )
        with pytest.raises(Exception, match="SL creation failed"):
            await cmd.execute()

        assert cmd.executed is False
        assert cmd.error is not None

    async def test_undo_success(self, mock_client):
        cmd = CreateStopLossCommand(
            client=mock_client,
            symbol="BTCUSDT",
            side="sell",
            quantity=0.1,
            stop_price=49000.0,
        )
        await cmd.execute()
        await cmd.undo()

        mock_client.cancel_all_orders.assert_awaited_once_with("BTCUSDT")

    async def test_undo_not_executed(self, mock_client):
        cmd = CreateStopLossCommand(
            client=mock_client,
            symbol="BTCUSDT",
            side="sell",
            quantity=0.1,
            stop_price=49000.0,
        )
        await cmd.undo()

        mock_client.cancel_all_orders.assert_not_awaited()
