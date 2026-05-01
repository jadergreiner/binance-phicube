"""Testes unitários do cache frio do painel."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from src.dashboard.cache import DashboardCache
from src.dashboard.models import PositionView


class _FakeCollection:
    def __init__(self) -> None:
        self.document: dict[str, object] | None = None
        self.fail_replace = False
        self.replace_calls: list[dict[str, object]] = []

    async def replace_one(
        self,
        filter_query: dict[str, object],
        document: dict[str, object],
        *,
        upsert: bool,
    ) -> None:
        self.replace_calls.append(
            {
                "filter": filter_query,
                "document": document,
                "upsert": upsert,
            }
        )
        if self.fail_replace:
            raise RuntimeError("mongo indisponivel")
        self.document = document

    async def find_one(self, filter_query: dict[str, object]) -> dict[str, object] | None:
        if self.document is None:
            return None
        if self.document.get("_id") != filter_query.get("_id"):
            return None
        return self.document


async def _wait_until(predicate: Any, *, timeout: float = 1.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("Condição esperada não foi satisfeita a tempo")


class _FakeDatabase:
    def __init__(self, collection: _FakeCollection) -> None:
        self._collection = collection

    def __getitem__(self, name: str) -> _FakeCollection:
        assert name == "dashboard_snapshot"
        return self._collection


def _make_position() -> PositionView:
    return PositionView(
        symbol="BTCUSDT",
        side="LONG",
        quantity=0.5,
        leverage=10,
        entry_price=95000.0,
        mark_price=96000.0,
        unrealized_pnl_usdt=250.0,
        margin_used_usdt=2400.0,
        liquidation_price=87000.0,
        updated_at=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_snapshot_salvo_com_cached_at_correto() -> None:
    collection = _FakeCollection()
    cache = DashboardCache(_FakeDatabase(collection))

    cache.save_snapshot([_make_position()])
    await _wait_until(lambda: len(collection.replace_calls) == 1)

    saved_document = cast(dict[str, Any], collection.replace_calls[0]["document"])
    assert saved_document["_id"] == "latest"
    assert saved_document["positions"][0]["symbol"] == "BTCUSDT"
    assert saved_document["cached_at"].tzinfo == UTC


@pytest.mark.asyncio
async def test_falha_de_escrita_no_mongo_e_logada_sem_propagar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collection = _FakeCollection()
    collection.fail_replace = True
    cache = DashboardCache(_FakeDatabase(collection))
    warning_mock = MagicMock()

    monkeypatch.setattr("src.dashboard.cache.logger.warning", warning_mock)

    cache.save_snapshot([_make_position()])
    await _wait_until(lambda: len(collection.replace_calls) == 1)

    warning_mock.assert_called_once()
    assert warning_mock.call_args.args[0] == "dashboard_snapshot_cache_save_failed"


@pytest.mark.asyncio
async def test_load_snapshot_retorna_none_quando_colecao_vazia() -> None:
    cache = DashboardCache(_FakeDatabase(_FakeCollection()))

    assert await cache.load_snapshot() is None


@pytest.mark.asyncio
async def test_load_snapshot_retorna_lista_correta_quando_ha_snapshot_salvo() -> None:
    collection = _FakeCollection()
    cached_at = datetime(2026, 5, 1, 12, 30, tzinfo=UTC)
    position = _make_position()
    collection.document = {
        "_id": "latest",
        "positions": [
            {
                "symbol": position.symbol,
                "side": position.side,
                "quantity": position.quantity,
                "leverage": position.leverage,
                "entry_price": position.entry_price,
                "mark_price": position.mark_price,
                "unrealized_pnl_usdt": position.unrealized_pnl_usdt,
                "margin_used_usdt": position.margin_used_usdt,
                "liquidation_price": position.liquidation_price,
                "updated_at": position.updated_at,
            }
        ],
        "cached_at": cached_at,
    }
    cache = DashboardCache(_FakeDatabase(collection))

    loaded_positions = await cache.load_snapshot()

    assert loaded_positions is not None
    assert loaded_positions == [position]


@pytest.mark.asyncio
async def test_load_snapshot_normaliza_datetime_naive_e_preserva_liquidation_price_none() -> None:
    collection = _FakeCollection()
    collection.document = {
        "_id": "latest",
        "positions": [
            {
                "symbol": "ETHUSDT",
                "side": "SHORT",
                "quantity": -1.5,
                "leverage": 8,
                "entry_price": 1800.0,
                "mark_price": 1750.0,
                "unrealized_pnl_usdt": 75.0,
                "margin_used_usdt": 430.0,
                "liquidation_price": None,
                "updated_at": datetime(2026, 5, 1, 12, 30),
            }
        ],
        "cached_at": datetime(2026, 5, 1, 12, 31, tzinfo=UTC),
    }
    cache = DashboardCache(_FakeDatabase(collection))

    loaded_positions = await cache.load_snapshot()

    assert loaded_positions is not None
    assert loaded_positions[0].liquidation_price is None
    assert loaded_positions[0].updated_at.tzinfo == UTC
    assert loaded_positions[0].updated_at == datetime(2026, 5, 1, 12, 30, tzinfo=UTC)
