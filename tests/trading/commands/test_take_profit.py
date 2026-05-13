"""Testes para CreateTakeProfitCommand."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.trading.commands.take_profit import CreateTakeProfitCommand


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.round_price = MagicMock(side_effect=lambda s, p: round(p, 2))
    client.create_take_profit_order = AsyncMock(
        return_value={
            "id": "tp_123",
            "status": "open",
        }
    )
    client.cancel_all_orders = AsyncMock(return_value=None)
    return client


class TestCreateTakeProfitCommand:
    async def test_execute_success(self, mock_client):
        cmd = CreateTakeProfitCommand(
            client=mock_client,
            symbol="BTCUSDT",
            side="sell",
            quantity=0.1,
            take_profit_price=51000.0,
        )
        result = await cmd.execute()

        assert result["id"] == "tp_123"
        assert cmd.executed is True
        mock_client.create_take_profit_order.assert_awaited_once_with(
            symbol="BTCUSDT",
            side="sell",
            quantity=0.1,
            take_profit_price=51000.0,
        )

    async def test_execute_failure(self, mock_client):
        mock_client.create_take_profit_order = AsyncMock(
            side_effect=Exception("TP creation failed")
        )
        cmd = CreateTakeProfitCommand(
            client=mock_client,
            symbol="BTCUSDT",
            side="sell",
            quantity=0.1,
            take_profit_price=51000.0,
        )
        with pytest.raises(Exception, match="TP creation failed"):
            await cmd.execute()

        assert cmd.executed is False
        assert cmd.error is not None

    async def test_undo_success(self, mock_client):
        cmd = CreateTakeProfitCommand(
            client=mock_client,
            symbol="BTCUSDT",
            side="sell",
            quantity=0.1,
            take_profit_price=51000.0,
        )
        await cmd.execute()
        await cmd.undo()

        mock_client.cancel_all_orders.assert_awaited_once_with("BTCUSDT")

    async def test_undo_not_executed(self, mock_client):
        cmd = CreateTakeProfitCommand(
            client=mock_client,
            symbol="BTCUSDT",
            side="sell",
            quantity=0.1,
            take_profit_price=51000.0,
        )
        await cmd.undo()

        mock_client.cancel_all_orders.assert_not_awaited()
