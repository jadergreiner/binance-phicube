"""Testes de resiliência do MongoRepository (SPEC_007 task_002)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymongo.errors import DuplicateKeyError

from src.trading.order_manager import Trade, TradeStatus


def _make_repo():
    """Instancia MongoRepository com cliente motor completamente mockado."""
    with patch("motor.motor_asyncio.AsyncIOMotorClient"):
        from src.storage.repository import MongoRepository

        repo = MongoRepository("mongodb://localhost/test", "test_db")
        return repo


def _make_trade() -> Trade:
    from datetime import UTC, datetime

    from src.trading.order_manager import Direction

    return Trade(
        entry_order_id="order_123",
        symbol="BTCUSDT",
        timeframe="4h",
        direction=Direction.LONG,
        quantity=0.01,
        entry_price=50000.0,
        stop_loss=49000.0,
        take_profit=52000.0,
        status=TradeStatus.OPEN,
        opened_at=datetime.now(UTC),
        risk_amount=10.0,
        margin_used=100.0,
    )


class TestSaveTradeDuplicateKeyError:
    """TEST_007_06 — save_trade captura DuplicateKeyError sem crash."""

    @pytest.mark.asyncio
    async def test_duplicate_key_retorna_none_sem_crash(self) -> None:
        """TEST_007_06: DuplicateKeyError em insert_one → None, sem relançar."""
        repo = _make_repo()
        mock_collection = AsyncMock()
        mock_collection.insert_one = AsyncMock(
            side_effect=DuplicateKeyError("duplicate entry_order_id")
        )
        repo._db = MagicMock()
        repo._db.__getitem__ = MagicMock(return_value=mock_collection)

        trade = _make_trade()
        result = await repo.save_trade(trade)

        assert result is None

    @pytest.mark.asyncio
    async def test_save_trade_normal_retorna_doc_id(self) -> None:
        """save_trade sem conflito retorna doc_id como string."""
        repo = _make_repo()
        mock_result = MagicMock()
        mock_result.inserted_id = "507f1f77bcf86cd799439011"
        mock_collection = AsyncMock()
        mock_collection.insert_one = AsyncMock(return_value=mock_result)
        repo._db = MagicMock()
        repo._db.__getitem__ = MagicMock(return_value=mock_collection)

        trade = _make_trade()
        result = await repo.save_trade(trade)

        assert result == "507f1f77bcf86cd799439011"

    @pytest.mark.asyncio
    async def test_duplicate_key_loga_warning(self, capfd) -> None:
        """DuplicateKeyError deve gerar log warning com entry_order_id.

        structlog escreve em stdout nos testes — capfd captura o output real.
        """
        repo = _make_repo()
        mock_collection = AsyncMock()
        mock_collection.insert_one = AsyncMock(side_effect=DuplicateKeyError("dup"))
        repo._db = MagicMock()
        repo._db.__getitem__ = MagicMock(return_value=mock_collection)

        trade = _make_trade()
        await repo.save_trade(trade)

        captured = capfd.readouterr()
        output = captured.out + captured.err
        assert "trade_duplicado_ignorado" in output
        assert "order_123" in output
