"""Testes de update_trade_status ampliado e get_performance_metrics (SPEC_006 tasks 002-003)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.trading.order_manager import TradeStatus


def _make_repo():
    """Instancia MongoRepository com cliente motor completamente mockado."""
    with patch("motor.motor_asyncio.AsyncIOMotorClient"):
        from src.storage.repository import MongoRepository

        repo = MongoRepository("mongodb://localhost/test", "test_db")
        return repo


class TestUpdateTradeStatusAmplied:
    """TEST_006_03 — update_trade_status persiste novos campos RF-11."""

    @pytest.mark.asyncio
    async def test_persiste_exit_price_pnl_usdt_close_reason(self) -> None:
        repo = _make_repo()
        mock_collection = AsyncMock()
        mock_collection.update_one = AsyncMock()
        mock_collection.find_one = AsyncMock(
            return_value={"symbol": "BTCUSDT", "entry_price": 52000.0}
        )
        mock_audit = AsyncMock()
        repo._db = MagicMock()
        repo._db.__getitem__ = MagicMock(return_value=mock_collection)
        repo.audit = mock_audit

        await repo.update_trade_status(
            entry_order_id="ord_001",
            status=TradeStatus.CLOSED_TP,
            pnl=20.0,
            exit_price=52000.0,
            pnl_usdt=20.0,
            close_reason="TP",
        )

        mock_collection.update_one.assert_called_once()
        call_args = mock_collection.update_one.call_args
        update_doc = call_args[0][1]
        assert update_doc["$set"]["exit_price"] == 52000.0
        assert update_doc["$set"]["pnl_usdt"] == 20.0
        assert update_doc["$set"]["close_reason"] == "TP"
        assert update_doc["$set"]["status"] == TradeStatus.CLOSED_TP.value
        mock_audit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_retrocompativel_sem_novos_campos(self) -> None:
        """Chamada sem novos campos não deve incluí-los no $set."""
        repo = _make_repo()
        mock_collection = AsyncMock()
        mock_collection.update_one = AsyncMock()
        mock_collection.find_one = AsyncMock(
            return_value={"symbol": "BTCUSDT", "entry_price": 52000.0}
        )
        mock_audit = AsyncMock()
        repo._db = MagicMock()
        repo._db.__getitem__ = MagicMock(return_value=mock_collection)
        repo.audit = mock_audit

        await repo.update_trade_status(
            entry_order_id="ord_002",
            status=TradeStatus.CLOSED_SL,
        )

        call_args = mock_collection.update_one.call_args
        update_doc = call_args[0][1]
        assert "exit_price" not in update_doc["$set"]
        assert "pnl_usdt" not in update_doc["$set"]
        assert "close_reason" not in update_doc["$set"]
        mock_audit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_bloqueia_fechamento_com_entry_price_fora_da_faixa(self) -> None:
        repo = _make_repo()
        mock_collection = AsyncMock()
        mock_collection.update_one = AsyncMock()
        mock_collection.find_one = AsyncMock(
            return_value={"symbol": "BTCUSDT", "entry_price": 100.0}
        )
        mock_audit = AsyncMock()
        repo._db = MagicMock()
        repo._db.__getitem__ = MagicMock(return_value=mock_collection)
        repo.audit = mock_audit

        await repo.update_trade_status(
            entry_order_id="ord_003",
            status=TradeStatus.CLOSED_MANUAL,
            pnl_usdt=-10.0,
        )

        mock_collection.update_one.assert_not_called()
        mock_audit.assert_awaited_once()
        event_name = mock_audit.await_args.args[0]
        payload = mock_audit.await_args.args[1]
        assert event_name == "trade_close_blocked_invalid_entry_price"
        assert payload["entry_order_id"] == "ord_003"
        assert payload["symbol"] == "BTCUSDT"


class TestGetPerformanceMetrics:
    """TEST_006_04, TEST_006_05, TEST_006_06 — get_performance_metrics."""

    def _make_trade_doc(
        self,
        pnl_usdt: float,
        risk_amount: float = 10.0,
        status: str = TradeStatus.CLOSED_TP.value,
        closed_at: datetime | None = None,
    ) -> dict:
        return {
            "pnl_usdt": pnl_usdt,
            "risk_amount": risk_amount,
            "status": status,
            "closed_at": closed_at or datetime.now(UTC),
        }

    @pytest.mark.asyncio
    async def test_metricas_com_trades_mistos(self) -> None:
        """TEST_006_04: 3 TP + 2 SL → métricas calculadas corretamente."""
        repo = _make_repo()
        trades = [
            self._make_trade_doc(20.0, risk_amount=10.0),  # TP win
            self._make_trade_doc(15.0, risk_amount=10.0),  # TP win
            self._make_trade_doc(10.0, risk_amount=10.0),  # TP win
            self._make_trade_doc(-8.0, risk_amount=10.0, status=TradeStatus.CLOSED_SL.value),
            self._make_trade_doc(-6.0, risk_amount=10.0, status=TradeStatus.CLOSED_SL.value),
        ]

        mock_collection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=trades)
        mock_collection.find = MagicMock(return_value=mock_cursor)
        repo._db = MagicMock()
        repo._db.__getitem__ = MagicMock(return_value=mock_collection)

        metrics = await repo.get_performance_metrics()

        assert metrics["total_trades"] == 5
        assert metrics["win_rate_pct"] == 60.0
        assert abs(metrics["total_pnl_usdt"] - 31.0) < 0.01
        assert metrics["avg_rrr"] != 0.0
        assert metrics["profit_factor"] > 1.0
        # max_drawdown deve ser negativo (representa uma perda)
        assert metrics["max_drawdown_usdt"] <= 0.0

    @pytest.mark.asyncio
    async def test_metricas_sem_trades_retorna_zeros(self) -> None:
        """TEST_006_05: coleção vazia → zeros, sem exceção."""
        repo = _make_repo()
        mock_collection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_collection.find = MagicMock(return_value=mock_cursor)
        repo._db = MagicMock()
        repo._db.__getitem__ = MagicMock(return_value=mock_collection)

        metrics = await repo.get_performance_metrics()

        assert metrics["total_trades"] == 0
        assert metrics["win_rate_pct"] == 0.0
        assert metrics["total_pnl_usdt"] == 0.0
        assert metrics["avg_rrr"] == 0.0
        assert metrics["max_drawdown_usdt"] == 0.0
        assert metrics["profit_factor"] == 0.0

    @pytest.mark.asyncio
    async def test_profit_factor_sem_perdas_nao_divide_por_zero(self) -> None:
        """TEST_006_06: todos TP → profit_factor sem ZeroDivisionError."""
        repo = _make_repo()
        trades = [
            self._make_trade_doc(20.0),
            self._make_trade_doc(10.0),
        ]
        mock_collection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=trades)
        mock_collection.find = MagicMock(return_value=mock_cursor)
        repo._db = MagicMock()
        repo._db.__getitem__ = MagicMock(return_value=mock_collection)

        metrics = await repo.get_performance_metrics()

        assert metrics["profit_factor"] == 0.0  # gross_loss=0 → normalizado
        assert metrics["win_rate_pct"] == 100.0
        assert metrics["total_pnl_usdt"] == 30.0


class TestGetIntradayRealizedPnl:
    @pytest.mark.asyncio
    async def test_soma_pnl_realizado_do_dia(self) -> None:
        repo = _make_repo()
        mock_collection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(
            return_value=[
                {"pnl_usdt": 10.0},
                {"pnl_usdt": -4.0},
                {"pnl_usdt": -1.5},
            ]
        )
        mock_collection.find = MagicMock(return_value=mock_cursor)
        repo._db = MagicMock()
        repo._db.__getitem__ = MagicMock(return_value=mock_collection)

        result = await repo.get_intraday_realized_pnl_usdt(
            now=datetime(2026, 5, 8, 12, 0, tzinfo=UTC)
        )

        assert result == 4.5
        query = mock_collection.find.call_args.args[0]
        assert "closed_at" in query
        assert "$gte" in query["closed_at"]
