"""Testes unitários do stream de posições do painel."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import WSMsgType

from src.dashboard.client import DashboardClient
from src.dashboard.models import PositionView
from src.dashboard.stream import PositionStream


def _make_settings(*, binance_testnet: bool = True) -> MagicMock:
    settings = MagicMock()
    settings.dashboard_api_key = "test_key"
    settings.dashboard_api_secret = "test_secret"
    settings.binance_testnet = binance_testnet
    return settings


def _make_snapshot_payload() -> list[dict[str, Any]]:
    return [
        {
            "symbol": "BTCUSDT",
            "positionAmt": "0.5",
            "leverage": "10",
            "entryPrice": "95000",
            "markPrice": "96000",
            "unRealizedProfit": "250",
            "isolatedMargin": "2400",
            "liquidationPrice": "87000",
        }
    ]


def _make_account_update_payload() -> dict[str, Any]:
    return {
        "e": "ACCOUNT_UPDATE",
        "a": {
            "P": [
                {
                    "s": "BTCUSDT",
                    "pa": "0.75",
                    "ep": "95500",
                    "up": "300",
                    "iw": "2500",
                }
            ]
        },
    }


async def _wait_until(predicate: Any, *, timeout: float = 1.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("Condição esperada não foi satisfeita a tempo")


class _FakeWebSocket:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[Any] = asyncio.Queue()
        self.closed = False

    async def receive(self) -> Any:
        if self.closed:
            return SimpleNamespace(type=WSMsgType.CLOSED, data=None)
        return await self._queue.get()

    async def close(self) -> None:
        self.closed = True

    async def push_json(self, payload: dict[str, Any]) -> None:
        await self._queue.put(SimpleNamespace(type=WSMsgType.TEXT, data=json.dumps(payload)))


class _FakeSession:
    def __init__(self, websocket: _FakeWebSocket) -> None:
        self._websocket = websocket
        self.closed = False
        self.connected_urls: list[str] = []

    async def ws_connect(self, url: str, *, heartbeat: int) -> _FakeWebSocket:
        self.connected_urls.append(f"{url}|heartbeat={heartbeat}")
        return self._websocket

    async def close(self) -> None:
        self.closed = True


class _FailingSession:
    def __init__(self) -> None:
        self.closed = False

    async def ws_connect(self, url: str, *, heartbeat: int) -> Any:
        raise OSError("stream indisponível")

    async def close(self) -> None:
        self.closed = True


class _StubCache:
    def __init__(self, positions: list[PositionView] | None = None) -> None:
        self._positions = positions
        self.saved_snapshots: list[list[PositionView]] = []

    def save_snapshot(self, positions: list[PositionView]) -> None:
        self.saved_snapshots.append(list(positions))

    async def load_snapshot(self) -> list[PositionView] | None:
        return self._positions


def _make_cached_position() -> PositionView:
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
async def test_snapshot_inicial_e_mapeado_para_position_view() -> None:
    client = DashboardClient(_make_settings())
    websocket = _FakeWebSocket()
    session = _FakeSession(websocket)

    client._exchange.fapiPrivateV2GetPositionRisk = AsyncMock(return_value=_make_snapshot_payload())
    client._exchange.fapiPrivatePostListenKey = AsyncMock(return_value={"listenKey": "listen-key"})
    client._exchange.fapiPrivatePutListenKey = AsyncMock(return_value={})
    client._exchange.fapiPrivateDeleteListenKey = AsyncMock(return_value={})

    stream = PositionStream(
        client,
        session_factory=lambda: session,
        keepalive_interval=3600,
    )

    await stream.start()

    positions = stream.get_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "BTCUSDT"
    assert positions[0].side == "LONG"
    assert positions[0].quantity == pytest.approx(0.5)
    assert positions[0].leverage == 10
    assert positions[0].entry_price == pytest.approx(95000.0)
    assert positions[0].mark_price == pytest.approx(96000.0)
    assert positions[0].unrealized_pnl_usdt == pytest.approx(250.0)
    assert positions[0].margin_used_usdt == pytest.approx(2400.0)
    assert positions[0].liquidation_price == pytest.approx(87000.0)
    assert stream.get_status() == "online"
    assert session.connected_urls == ["wss://stream.binancefuture.com/ws/listen-key|heartbeat=30"]

    await stream.stop()


@pytest.mark.asyncio
async def test_account_update_atualiza_posicao_correta_em_memoria() -> None:
    client = DashboardClient(_make_settings())
    websocket = _FakeWebSocket()
    session = _FakeSession(websocket)

    client._exchange.fapiPrivateV2GetPositionRisk = AsyncMock(return_value=_make_snapshot_payload())
    client._exchange.fapiPrivatePostListenKey = AsyncMock(return_value={"listenKey": "listen-key"})
    client._exchange.fapiPrivatePutListenKey = AsyncMock(return_value={})
    client._exchange.fapiPrivateDeleteListenKey = AsyncMock(return_value={})

    stream = PositionStream(
        client,
        session_factory=lambda: session,
        keepalive_interval=3600,
    )

    await stream.start()
    previous_updated_at = stream.get_positions()[0].updated_at

    await websocket.push_json(_make_account_update_payload())
    await _wait_until(lambda: stream.get_positions()[0].quantity == pytest.approx(0.75))

    position = stream.get_positions()[0]
    assert position.symbol == "BTCUSDT"
    assert position.side == "LONG"
    assert position.quantity == pytest.approx(0.75)
    assert position.entry_price == pytest.approx(95500.0)
    assert position.unrealized_pnl_usdt == pytest.approx(300.0)
    assert position.margin_used_usdt == pytest.approx(2500.0)
    assert position.mark_price == pytest.approx(96000.0)
    assert position.leverage == 10
    assert position.updated_at > previous_updated_at

    await stream.stop()


@pytest.mark.asyncio
async def test_falha_de_stream_altera_status_para_degraded_sem_propagar_excecao() -> None:
    client = DashboardClient(_make_settings())
    statuses: list[str] = []

    client._exchange.fapiPrivateV2GetPositionRisk = AsyncMock(return_value=_make_snapshot_payload())
    client._exchange.fapiPrivatePostListenKey = AsyncMock(return_value={"listenKey": "listen-key"})
    client._exchange.fapiPrivateDeleteListenKey = AsyncMock(return_value={})

    stream = PositionStream(
        client,
        on_status_change=statuses.append,
        session_factory=_FailingSession,
        keepalive_interval=3600,
    )

    await stream.start()

    assert stream.get_positions()[0].symbol == "BTCUSDT"
    assert stream.get_status() == "degraded"
    assert stream.degraded_event.is_set() is True
    assert statuses == ["degraded"]

    await stream.stop()


@pytest.mark.asyncio
async def test_snapshot_rest_fallback_para_cache_na_inicializacao() -> None:
    client = DashboardClient(_make_settings())
    websocket = _FakeWebSocket()
    session = _FakeSession(websocket)
    cache = _StubCache([_make_cached_position()])

    client._exchange.fapiPrivateV2GetPositionRisk = AsyncMock(
        side_effect=RuntimeError("rest indisponivel")
    )
    client._exchange.fapiPrivatePostListenKey = AsyncMock(return_value={"listenKey": "listen-key"})
    client._exchange.fapiPrivatePutListenKey = AsyncMock(return_value={})
    client._exchange.fapiPrivateDeleteListenKey = AsyncMock(return_value={})

    stream = PositionStream(
        client,
        cache=cache,
        session_factory=lambda: session,
        keepalive_interval=3600,
    )

    await stream.start()

    positions = stream.get_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "BTCUSDT"
    assert stream.get_status() == "cached"
    assert session.connected_urls == ["wss://stream.binancefuture.com/ws/listen-key|heartbeat=30"]

    await stream.stop()


@pytest.mark.asyncio
async def test_snapshot_valido_e_salvo_no_cache_apos_update() -> None:
    client = DashboardClient(_make_settings())
    websocket = _FakeWebSocket()
    session = _FakeSession(websocket)
    cache = _StubCache()

    client._exchange.fapiPrivateV2GetPositionRisk = AsyncMock(return_value=_make_snapshot_payload())
    client._exchange.fapiPrivatePostListenKey = AsyncMock(return_value={"listenKey": "listen-key"})
    client._exchange.fapiPrivatePutListenKey = AsyncMock(return_value={})
    client._exchange.fapiPrivateDeleteListenKey = AsyncMock(return_value={})

    stream = PositionStream(
        client,
        cache=cache,
        session_factory=lambda: session,
        keepalive_interval=3600,
    )

    await stream.start()
    await websocket.push_json(_make_account_update_payload())
    await _wait_until(lambda: len(cache.saved_snapshots) >= 2)

    latest_snapshot = cache.saved_snapshots[-1]
    assert latest_snapshot[0].symbol == "BTCUSDT"
    assert latest_snapshot[0].quantity == pytest.approx(0.75)

    await stream.stop()


@pytest.mark.asyncio
async def test_keepalive_com_falha_fecha_transporte_e_marca_stream_como_degraded() -> None:
    client = DashboardClient(_make_settings())
    websocket = _FakeWebSocket()
    session = _FakeSession(websocket)
    statuses: list[str] = []

    client._exchange.fapiPrivateV2GetPositionRisk = AsyncMock(return_value=_make_snapshot_payload())
    client._exchange.fapiPrivatePostListenKey = AsyncMock(return_value={"listenKey": "listen-key"})
    client._exchange.fapiPrivatePutListenKey = AsyncMock(
        side_effect=RuntimeError("keepalive falhou")
    )
    client._exchange.fapiPrivateDeleteListenKey = AsyncMock(return_value={})

    stream = PositionStream(
        client,
        on_status_change=statuses.append,
        session_factory=lambda: session,
        keepalive_interval=0.01,
    )

    await stream.start()
    await _wait_until(lambda: stream.get_status() == "degraded")

    assert websocket.closed is True
    assert session.closed is True
    assert statuses[-1] == "degraded"
    client._exchange.fapiPrivateDeleteListenKey.assert_awaited()

    await stream.stop()
