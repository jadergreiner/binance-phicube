"""Testes unitários da API do dashboard de consulta de posições."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.api import main as api_main


class _FakeStream:
    def __init__(self, *, positions: list[object], status: str) -> None:
        self._positions = positions
        self._status = status

    def get_positions(self) -> list[object]:
        return list(self._positions)

    def get_status(self) -> str:
        return self._status


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
    monkeypatch.setattr(api_main.PositionStream, "start", AsyncMock(return_value=None))
    monkeypatch.setattr(api_main.PositionStream, "stop", AsyncMock(return_value=None))
    monkeypatch.setattr(api_main.AdaptiveUpdater, "start", AsyncMock(return_value=None))
    monkeypatch.setattr(api_main.AdaptiveUpdater, "stop", AsyncMock(return_value=None))


def test_lifespan_inicializa_e_encerra_recursos_na_ordem_correta(monkeypatch) -> None:
    """O lifespan deve inicializar e encerrar os recursos do dashboard na ordem esperada."""
    eventos: list[str] = []
    app = api_main.create_app()

    async def _connect(self) -> None:
        eventos.append("connect")

    async def _close(self) -> None:
        eventos.append("close")

    async def _stream_start(self) -> None:
        eventos.append("stream.start")

    async def _stream_stop(self) -> None:
        eventos.append("stream.stop")

    async def _updater_start(self, stream) -> None:
        eventos.append("updater.start")
        assert stream is app.state.position_stream

    async def _updater_stop(self) -> None:
        eventos.append("updater.stop")

    monkeypatch.setattr(
        api_main,
        "get_settings",
        lambda: SimpleNamespace(
            dashboard_api_key="dash_key",
            dashboard_api_secret="dash_secret",
            binance_testnet=True,
        ),
    )
    monkeypatch.setattr(api_main.DashboardClient, "connect", _connect)
    monkeypatch.setattr(api_main.DashboardClient, "close", _close)
    monkeypatch.setattr(api_main.PositionStream, "start", _stream_start)
    monkeypatch.setattr(api_main.PositionStream, "stop", _stream_stop)
    monkeypatch.setattr(api_main.AdaptiveUpdater, "start", _updater_start)
    monkeypatch.setattr(api_main.AdaptiveUpdater, "stop", _updater_stop)

    with TestClient(app) as client:
        assert client.app.state.stream is client.app.state.position_stream
        assert client.app.state.dashboard_client is not None

    assert eventos == [
        "connect",
        "stream.start",
        "updater.start",
        "updater.stop",
        "stream.stop",
        "close",
    ]


def test_get_positions_retorna_snapshot_json_valido(monkeypatch) -> None:
    """GET /positions deve devolver posições e resumo agregados."""
    _patch_lifespan(monkeypatch)

    with TestClient(api_main.create_app()) as client:
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
    assert response.json() == {
        "positions": [
            {
                "symbol": "BTCUSDT",
                "side": "LONG",
                "quantity": 0.5,
                "leverage": 10,
                "entry_price": 95000.0,
                "mark_price": 96000.0,
                "unrealized_pnl_usdt": 250.0,
                "margin_used_usdt": 2400.0,
                "liquidation_price": 87000.0,
                "updated_at": "2026-05-01T12:30:00Z",
            }
        ],
        "summary": {
            "total_exposure_usdt": 48000.0,
            "total_margin_used_usdt": 2400.0,
            "total_unrealized_pnl_usdt": 250.0,
            "connection_status": "online",
            "last_update_at": "2026-05-01T12:30:00Z",
        },
        "status": "online",
    }


def test_get_health_retorna_status_degradado(monkeypatch) -> None:
    """GET /health deve refletir o status real do stream."""
    _patch_lifespan(monkeypatch)

    with TestClient(api_main.create_app()) as client:
        client.app.state.position_stream = _FakeStream(positions=[], status="degraded")

        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "degraded"}


def test_get_positions_retornara_503_quando_stream_inativo(monkeypatch) -> None:
    """GET /positions deve retornar 503 quando o stream estiver offline."""
    _patch_lifespan(monkeypatch)

    with TestClient(api_main.create_app()) as client:
        client.app.state.position_stream = _FakeStream(positions=[], status="offline")

        response = client.get("/positions")

    assert response.status_code == 503
    assert response.json() == {"status": "offline"}