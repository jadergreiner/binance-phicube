"""Testes de histórico de trades (SPEC_016)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.trades import router
from src.trading.order_manager import TradeStatus


def _make_app(repo=None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    if repo is not None:
        app.state.repository = repo
    return app


def _make_repo():
    with patch("motor.motor_asyncio.AsyncIOMotorClient"):
        from src.storage.repository import MongoRepository

        return MongoRepository("mongodb://localhost/test", "test_db")


class TestTradeHistoryEndpoint:
    def test_retorna_200_com_ate_50_trades(self) -> None:
        trades = [
            {
                "symbol": f"SYM{i}",
                "timeframe": "1h",
                "direction": "long",
                "entry_price": 10.0,
                "exit_price": 11.0,
                "stop_loss": 9.0,
                "take_profit": 12.0,
                "pnl_usdt": 1.0,
                "status": "CLOSED_TP",
                "opened_at": datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
                "closed_at": datetime(2026, 5, 1, 13, 0, tzinfo=UTC),
            }
            for i in range(50)
        ]
        repo = AsyncMock()
        repo.get_trade_history = AsyncMock(return_value=trades)

        app = _make_app(repo=repo)
        with TestClient(app) as client:
            response = client.get("/trades/history")

        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 50
        assert len(payload["trades"]) == 50
        assert payload["trades"][0]["closed_at"].endswith("Z")
        repo.get_trade_history.assert_awaited_once_with(limit=50)

    def test_retorna_200_com_array_vazio_sem_trades(self) -> None:
        repo = AsyncMock()
        repo.get_trade_history = AsyncMock(return_value=[])

        app = _make_app(repo=repo)
        with TestClient(app) as client:
            response = client.get("/trades/history")

        assert response.status_code == 200
        assert response.json()["trades"] == []
        assert response.json()["total"] == 0

    def test_retorna_503_sem_repositorio(self) -> None:
        app = _make_app(repo=None)
        with TestClient(app) as client:
            response = client.get("/trades/history")

        assert response.status_code == 503
        assert response.json() == {"detail": "Repositório indisponível"}

    def test_retorna_503_quando_repositorio_falha(self) -> None:
        repo = AsyncMock()
        repo.get_trade_history = AsyncMock(side_effect=RuntimeError("db down"))

        app = _make_app(repo=repo)
        with TestClient(app) as client:
            response = client.get("/trades/history")

        assert response.status_code == 503
        assert response.json() == {"detail": "Repositório indisponível"}


class TestTradeHistoryRepository:
    @pytest.mark.asyncio
    async def test_get_trade_history_ordena_por_closed_at_desc(self) -> None:
        repo = _make_repo()
        returned = [
            {"symbol": "BTCUSDT", "status": TradeStatus.CLOSED_TP.value},
            {"symbol": "ETHUSDT", "status": TradeStatus.CLOSED_SL.value},
        ]
        aggregate_cursor = AsyncMock()
        aggregate_cursor.to_list = AsyncMock(return_value=returned)
        collection = MagicMock()
        collection.aggregate = MagicMock(return_value=aggregate_cursor)
        repo._db = MagicMock()
        repo._db.__getitem__ = MagicMock(return_value=collection)

        result = await repo.get_trade_history(limit=50)

        assert result == returned
        pipeline = collection.aggregate.call_args.args[0]
        assert pipeline[0]["$match"]["status"]["$in"] == [
            TradeStatus.CLOSED_TP.value,
            TradeStatus.CLOSED_SL.value,
            TradeStatus.CLOSED_MANUAL.value,
        ]
        assert pipeline[1] == {"$sort": {"closed_at": -1}}
        assert pipeline[2] == {"$limit": 50}
