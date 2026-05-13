"""Testes para CreateMarketOrderCommand."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.trading.commands.market_order import CreateMarketOrderCommand


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.create_market_order = AsyncMock(
        return_value={
            "id": "order_123",
            "average": 50000.0,
            "status": "filled",
        }
    )
    client.cancel_all_orders = AsyncMock(return_value=None)
    return client


class TestCreateMarketOrderCommand:
    async def test_execute_success(self, mock_client):
        cmd = CreateMarketOrderCommand(
            client=mock_client,
            symbol="BTCUSDT",
            side="buy",
            quantity=0.1,
        )
        result = await cmd.execute()

        assert result["id"] == "order_123"
        assert result["average"] == 50000.0
        assert cmd.executed is True
        assert cmd.result == result
        mock_client.create_market_order.assert_awaited_once_with(
            symbol="BTCUSDT",
            side="buy",
            quantity=0.1,
        )

    async def test_execute_failure(self, mock_client):
        mock_client.create_market_order = AsyncMock(side_effect=Exception("Insufficient balance"))
        cmd = CreateMarketOrderCommand(
            client=mock_client,
            symbol="BTCUSDT",
            side="buy",
            quantity=0.1,
        )
        with pytest.raises(Exception, match="Insufficient balance"):
            await cmd.execute()

        assert cmd.executed is False
        assert cmd.error is not None
        assert "Insufficient balance" in str(cmd.error)

    async def test_undo_success(self, mock_client):
        cmd = CreateMarketOrderCommand(
            client=mock_client,
            symbol="BTCUSDT",
            side="buy",
            quantity=0.1,
        )
        await cmd.execute()
        await cmd.undo()

        mock_client.cancel_all_orders.assert_awaited_once_with("BTCUSDT")

    async def test_undo_not_executed(self, mock_client):
        cmd = CreateMarketOrderCommand(
            client=mock_client,
            symbol="BTCUSDT",
            side="buy",
            quantity=0.1,
        )
        await cmd.undo()

        # Não deve chamar cancel_all_orders se não foi executado
        mock_client.cancel_all_orders.assert_not_awaited()

    async def test_undo_failure(self, mock_client):
        mock_client.cancel_all_orders = AsyncMock(side_effect=Exception("Cancel failed"))
        cmd = CreateMarketOrderCommand(
            client=mock_client,
            symbol="BTCUSDT",
            side="buy",
            quantity=0.1,
        )
        await cmd.execute()

        with pytest.raises(Exception, match="Cancel failed"):
            await cmd.undo()
