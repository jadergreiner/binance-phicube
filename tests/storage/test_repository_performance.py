"""Testes para get_performance_by_symbol e get_performance_by_timeframe (SPEC_009)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.trading.order_manager import TradeStatus


def _make_repo():
    with patch("motor.motor_asyncio.AsyncIOMotorClient"):
        from src.storage.repository import MongoRepository

        return MongoRepository("mongodb://localhost/test", "test_db")


def _trade(pnl_usdt: float, symbol: str, timeframe: str, risk_amount: float = 10.0) -> dict:
    return {
        "pnl_usdt": pnl_usdt,
        "risk_amount": risk_amount,
        "symbol": symbol,
        "timeframe": timeframe,
        "closed_at": datetime.now(UTC),
        "status": TradeStatus.CLOSED_TP.value,
    }


def _mock_find(repo, trades: list[dict]) -> None:
    mock_collection = AsyncMock()
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=trades)
    mock_collection.find = MagicMock(return_value=mock_cursor)
    repo._db = MagicMock()
    repo._db.__getitem__ = MagicMock(return_value=mock_collection)


class TestGetPerformanceBySymbol:
    """TEST_009_01 e TEST_009_02 — get_performance_by_symbol."""

    @pytest.mark.asyncio
    async def test_retorna_metricas_por_simbolo(self) -> None:
        """TEST_009_01: 2 símbolos → métricas independentes por símbolo."""
        repo = _make_repo()
        trades = [
            _trade(20.0, "BTCUSDT", "4h"),
            _trade(10.0, "BTCUSDT", "4h"),
            _trade(-5.0, "ETHUSDT", "1d"),
        ]
        _mock_find(repo, trades)

        result = await repo.get_performance_by_symbol()

        assert set(result.keys()) == {"BTCUSDT", "ETHUSDT"}
        assert result["BTCUSDT"]["total_trades"] == 2
        assert result["BTCUSDT"]["win_rate_pct"] == 100.0
        assert abs(result["BTCUSDT"]["total_pnl_usdt"] - 30.0) < 0.01
        assert result["ETHUSDT"]["total_trades"] == 1
        assert result["ETHUSDT"]["win_rate_pct"] == 0.0
        assert result["ETHUSDT"]["total_pnl_usdt"] < 0
        query = repo._db.__getitem__.return_value.find.call_args.args[0]
        assert query["excluded_from_metrics"] == {"$ne": True}

    @pytest.mark.asyncio
    async def test_retorna_dict_vazio_sem_trades(self) -> None:
        """TEST_009_02: sem trades fechados → dict vazio."""
        repo = _make_repo()
        _mock_find(repo, [])

        result = await repo.get_performance_by_symbol()

        assert result == {}


class TestGetPerformanceByTimeframe:
    """TEST_009_03 — get_performance_by_timeframe."""

    @pytest.mark.asyncio
    async def test_retorna_metricas_por_timeframe(self) -> None:
        """TEST_009_03: 2 timeframes → métricas independentes por timeframe."""
        repo = _make_repo()
        trades = [
            _trade(15.0, "BTCUSDT", "4h"),
            _trade(-8.0, "BTCUSDT", "4h"),
            _trade(25.0, "ETHUSDT", "1d"),
        ]
        _mock_find(repo, trades)

        result = await repo.get_performance_by_timeframe()

        assert set(result.keys()) == {"4h", "1d"}
        assert result["4h"]["total_trades"] == 2
        assert result["1d"]["total_trades"] == 1
        assert result["1d"]["win_rate_pct"] == 100.0


class TestGetPerformanceMetricsNonBreaking:
    """TEST_009_04 — get_performance_metrics continua funcionando após refactor."""

    @pytest.mark.asyncio
    async def test_get_performance_metrics_identico_apos_refactor(self) -> None:
        """TEST_009_04: refactor de _calc_metrics não altera comportamento existente."""
        repo = _make_repo()
        trades = [
            {"pnl_usdt": 20.0, "risk_amount": 10.0, "closed_at": datetime.now(UTC)},
            {"pnl_usdt": -8.0, "risk_amount": 10.0, "closed_at": datetime.now(UTC)},
        ]
        _mock_find(repo, trades)

        metrics = await repo.get_performance_metrics()

        assert metrics["total_trades"] == 2
        assert metrics["win_rate_pct"] == 50.0
        assert abs(metrics["total_pnl_usdt"] - 12.0) < 0.01
        assert metrics["profit_factor"] > 0
        assert "max_drawdown_usdt" in metrics
        assert "avg_rrr" in metrics
        query = repo._db.__getitem__.return_value.find.call_args.args[0]
        assert query["excluded_from_metrics"] == {"$ne": True}
