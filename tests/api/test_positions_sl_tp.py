"""Testes de enriquecimento de posições com SL/TP (SPEC_016)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api import main as api_main


class _FakeStream:
    def __init__(self, *, positions: list[object], status: str) -> None:
        self._positions = positions
        self._status = status
        self._account_equity_usdt = None

    def get_positions(self) -> list[object]:
        return list(self._positions)

    def get_status(self) -> str:
        return self._status

    def get_account_equity_usdt(self) -> float | None:
        return self._account_equity_usdt


def _make_position(*, symbol: str, updated_at: datetime) -> SimpleNamespace:
    return SimpleNamespace(
        symbol=symbol,
        side="LONG",
        quantity=0.5,
        leverage=10,
        entry_price=95000.0,
        mark_price=96000.0,
        unrealized_pnl_usdt=250.0,
        margin_used_usdt=2400.0,
        liquidation_price=87000.0,
        updated_at=updated_at,
    )


def _make_repo():
    with patch("motor.motor_asyncio.AsyncIOMotorClient"):
        from src.storage.repository import MongoRepository

        return MongoRepository("mongodb://localhost/test", "test_db")


def _patch_lifespan(monkeypatch) -> None:
    monkeypatch.setattr(
        api_main,
        "get_settings",
        lambda: SimpleNamespace(
            dashboard_api_key="dash_key",
            dashboard_api_secret="dash_secret",
            binance_testnet=True,
        ),
    )
    monkeypatch.setattr(api_main.DashboardClient, "connect", AsyncMock(return_value=None))
    monkeypatch.setattr(api_main.DashboardClient, "close", AsyncMock(return_value=None))
    monkeypatch.setattr(api_main.PositionStream, "start", AsyncMock(return_value=True))
    monkeypatch.setattr(api_main.PositionStream, "get_status", lambda self: "online")
    monkeypatch.setattr(api_main.PositionStream, "stop", AsyncMock(return_value=None))
    monkeypatch.setattr(api_main.AdaptiveUpdater, "start", AsyncMock(return_value=None))
    monkeypatch.setattr(api_main.AdaptiveUpdater, "stop", AsyncMock(return_value=None))


def test_get_positions_enriquece_com_sl_tp(monkeypatch) -> None:
    _patch_lifespan(monkeypatch)
    repo = AsyncMock()
    repo.get_open_trade_sl_tp = AsyncMock(
        return_value={"BTCUSDT": {"sl_price": 93000.0, "tp_price": 98000.0}}
    )

    with TestClient(api_main.create_app()) as client:
        client.app.state.repository = repo
        client.app.state.position_stream = _FakeStream(
            positions=[
                _make_position(
                    symbol="BTCUSDT",
                    updated_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
                )
            ],
            status="online",
        )
        response = client.get("/positions")

    assert response.status_code == 200
    position = response.json()["positions"][0]
    assert position["sl_price"] == 93000.0
    assert position["tp_price"] == 98000.0


def test_get_positions_retorna_null_sem_trade_open(monkeypatch) -> None:
    _patch_lifespan(monkeypatch)
    repo = AsyncMock()
    repo.get_open_trade_sl_tp = AsyncMock(return_value={})

    with TestClient(api_main.create_app()) as client:
        client.app.state.repository = repo
        client.app.state.position_stream = _FakeStream(
            positions=[
                _make_position(
                    symbol="ETHUSDT",
                    updated_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
                )
            ],
            status="online",
        )
        response = client.get("/positions")

    assert response.status_code == 200
    position = response.json()["positions"][0]
    assert position["sl_price"] is None
    assert position["tp_price"] is None


class TestOpenTradeSlTpRepository:
    @pytest.mark.asyncio
    async def test_get_open_trade_sl_tp_retorna_dict_por_symbol(self) -> None:
        repo = _make_repo()
        mock_collection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(
            return_value=[
                {"symbol": "BTCUSDT", "stop_loss": 63000.0, "take_profit": 68000.0},
                {"symbol": "ETHUSDT", "stop_loss": 3000.0, "take_profit": 3500.0},
                {"symbol": "BNBUSDT", "stop_loss": None, "take_profit": 720.0},
            ]
        )
        mock_collection.find = MagicMock(return_value=mock_cursor)
        repo._db = MagicMock()
        repo._db.__getitem__ = MagicMock(return_value=mock_collection)

        result = await repo.get_open_trade_sl_tp()

        assert result == {
            "BTCUSDT": {"sl_price": 63000.0, "tp_price": 68000.0},
            "ETHUSDT": {"sl_price": 3000.0, "tp_price": 3500.0},
            "BNBUSDT": {"sl_price": None, "tp_price": 720.0},
        }
