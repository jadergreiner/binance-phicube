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
                "close_reason": "tp_executed",
                "is_estimated": False,
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
        assert payload["trades"][0]["closed_at_br"] == "01/05/2026 10:00:00"
        assert payload["trades"][0]["close_reason"] == "tp_executed"
        assert payload["trades"][0]["is_estimated"] is False
        assert payload["generated_at_br"]
        assert payload["timezone"] == "America/Sao_Paulo"
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


class TestOpenTradesEndpoint:
    def test_retorna_200_com_trades_abertos_enriquecidos(self) -> None:
        repo = AsyncMock()
        repo.get_open_trades = AsyncMock(
            return_value=[
                {
                    "symbol": "NATGAS/USDT:USDT",
                    "direction": "SHORT",
                    "quantity": 5.8,
                    "entry_price": 2.733,
                    "margin_used": 2.73,
                    "opened_at": datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
                    "status": "OPEN",
                }
            ]
        )
        app = _make_app(repo=repo)
        app.state.position_stream = MagicMock()
        app.state.position_stream.get_positions = MagicMock(
            return_value=[
                MagicMock(
                    symbol="NATGAS/USDT:USDT",
                    mark_price=2.841,
                    unrealized_pnl_usdt=-0.55,
                )
            ]
        )

        with TestClient(app) as client:
            response = client.get("/trades/open")

        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 1
        assert payload["trades"][0] == {
            "opened_at": "2026-05-01T12:00:00Z",
            "opened_at_br": "01/05/2026 09:00:00",
            "symbol": "NATGAS/USDT:USDT",
            "margin_used_usdt": 2.73,
            "entry_price": 2.733,
            "current_price": 2.841,
            "unrealized_pnl_usdt": -0.55,
        }
        assert payload["generated_at_br"]
        assert payload["timezone"] == "America/Sao_Paulo"

    def test_match_symbol_com_normalizacao_para_stream(self) -> None:
        repo = AsyncMock()
        repo.get_open_trades = AsyncMock(
            return_value=[
                {
                    "symbol": "BTC/USDT:USDT",
                    "direction": "LONG",
                    "quantity": 0.1,
                    "entry_price": 100000.0,
                    "margin_used": 2000.0,
                    "opened_at": datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
                    "status": "OPEN",
                }
            ]
        )
        app = _make_app(repo=repo)
        app.state.position_stream = MagicMock()
        app.state.position_stream.get_positions = MagicMock(
            return_value=[
                MagicMock(
                    symbol="BTCUSDT",
                    mark_price=101000.0,
                    unrealized_pnl_usdt=100.0,
                )
            ]
        )

        with TestClient(app) as client:
            response = client.get("/trades/open")

        assert response.status_code == 200
        trade = response.json()["trades"][0]
        assert trade["current_price"] == pytest.approx(101000.0)
        assert trade["unrealized_pnl_usdt"] == pytest.approx(100.0)

    def test_retorna_200_com_fallback_sem_stream(self) -> None:
        repo = AsyncMock()
        repo.get_open_trades = AsyncMock(
            return_value=[
                {
                    "symbol": "BTCUSDT",
                    "direction": "LONG",
                    "quantity": 0.1,
                    "entry_price": 100000.0,
                    "margin_used": 2000.0,
                    "opened_at": datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
                    "status": "OPEN",
                }
            ]
        )
        app = _make_app(repo=repo)

        with TestClient(app) as client:
            response = client.get("/trades/open")

        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 1
        assert payload["trades"][0]["current_price"] is None
        assert payload["trades"][0]["unrealized_pnl_usdt"] is None

    def test_retorna_503_sem_repositorio(self) -> None:
        app = _make_app(repo=None)
        with TestClient(app) as client:
            response = client.get("/trades/open")

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
        assert pipeline[3]["$project"]["close_reason"] == 1
        assert pipeline[3]["$project"]["is_estimated"] == 1
