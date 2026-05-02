"""Testes unitários do WebSocket do dashboard de consulta de posições."""

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
        self.on_update = None

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


def test_websocket_envia_snapshot_inicial_e_broadcast_na_atualizacao(monkeypatch) -> None:
    """O WS deve enviar snapshot imediato e broadcast quando o stream atualizar."""
    _patch_lifespan(monkeypatch)

    app = api_main.create_app()
    with TestClient(app) as client:
        stream = _FakeStream(
            positions=[
                _make_position(
                    symbol="BTCUSDT",
                    updated_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
                )
            ],
            status="online",
        )
        client.app.state.position_stream = stream

        with client.websocket_connect("/ws/positions") as websocket:
            initial_payload = websocket.receive_json()
            assert initial_payload["status"] == "online"
            assert initial_payload["positions"][0]["symbol"] == "BTCUSDT"

            stream._positions = [
                _make_position(
                    symbol="ETHUSDT",
                    updated_at=datetime(2026, 5, 1, 12, 31, tzinfo=UTC),
                )
            ]

            assert stream.on_update is not None
            client.portal.call(stream.on_update, stream)
            websocket_payload = websocket.receive_json()

        assert websocket_payload["positions"][0]["symbol"] == "ETHUSDT"
        assert websocket_payload["summary"]["connection_status"] == "online"