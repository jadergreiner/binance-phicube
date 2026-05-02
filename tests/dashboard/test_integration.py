from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsError
from fastapi.testclient import TestClient

try:
    from binance.um_futures import UMFutures
except ImportError:  # pragma: no cover - depende do ambiente de integração real
    UMFutures = None

from src.config.settings import get_settings
from src.dashboard.client import DashboardClient
from src.dashboard.models import PositionView
from src.dashboard.stream import PositionStream
from src.dashboard.updater import AdaptiveUpdater
from src.api import main as api_main


@dataclass(slots=True)
class _IntegrationSettings:
    dashboard_api_key: str
    dashboard_api_secret: str
    binance_testnet: bool = True


class _FakeStream:
    def __init__(self, *, positions: list[PositionView], status: str) -> None:
        self._positions = positions
        self._status = status
        self.on_update = None

    def get_positions(self) -> list[PositionView]:
        return list(self._positions)

    def get_status(self) -> str:
        return self._status


def _make_spec_002_position(*, symbol: str, updated_at: datetime) -> PositionView:
    return PositionView(
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


def _build_integration_settings_or_skip() -> _IntegrationSettings:
    get_settings.cache_clear()

    try:
        settings = get_settings()
        api_key = settings.dashboard_api_key.strip()
        api_secret = settings.dashboard_api_secret.strip()
    except (SettingsError, ValidationError) as exc:
        raise pytest.skip.Exception(
            "INT_001 bloqueado: .env ausente ou inválido para integração real. "
            "Configure DASHBOARD_API_KEY e DASHBOARD_API_SECRET com API Key READ_ONLY.",
        ) from exc

    if not api_key or not api_secret:
        pytest.skip(
            "INT_001 bloqueado: variáveis DASHBOARD_API_KEY/DASHBOARD_API_SECRET ausentes. "
            "Configure credenciais da Binance Futures em ambiente real ou Demo Trading "
            "com API Key READ_ONLY."
        )

    return _IntegrationSettings(
        dashboard_api_key=api_key,
        dashboard_api_secret=api_secret,
        binance_testnet=settings.binance_testnet,
    )


async def _build_client_or_skip() -> DashboardClient:
    if UMFutures is None:
        pytest.skip(
            "INT_001 bloqueado: SDK binance ausente no ambiente local. "
            "Os testes da SPEC_002 continuam válidos sem a integração real."
        )

    settings = _build_integration_settings_or_skip()
    futures_client = UMFutures(
        key=settings.dashboard_api_key,
        secret=settings.dashboard_api_secret,
    )

    try:
        await asyncio.wait_for(asyncio.to_thread(futures_client.account), timeout=20)
    except Exception as exc:
        pytest.skip(
            "INT_001 bloqueado: falha de acesso Binance Futures com SDK oficial "
            f"usando as credenciais informadas ({exc!r})."
        )

    return DashboardClient(settings)


async def _start_stream_or_skip(stream: PositionStream) -> None:
    try:
        await asyncio.wait_for(stream.start(), timeout=30)
    except Exception as exc:
        try:
            await stream.stop(status="offline")
        except Exception:
            pass

        pytest.skip(
            "INT_001 bloqueado: falha ao iniciar stream na Binance Futures "
            f"(erro: {exc!r}). Verifique rede/infra e disponibilidade dos serviços."
        )

    if stream.get_status() != "online":
        await stream.stop(status="offline")
        pytest.skip(
            "INT_001 bloqueado: stream não ficou online na Binance Futures após inicialização. "
            "Verifique conectividade e permissões da API key."
        )


async def _wait_until(
    predicate: Callable[[], bool],
    *,
    timeout: float = 30.0,
    interval: float = 0.2,
) -> None:
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        if predicate():
            return
        await asyncio.sleep(interval)
    raise TimeoutError(f"Condição não satisfeita em {timeout:.1f}s")


def _build_divergent_position() -> PositionView:
    return PositionView(
        symbol="FAKEUSDT",
        side="LONG",
        quantity=99.0,
        leverage=50,
        entry_price=12345.0,
        mark_price=12350.0,
        unrealized_pnl_usdt=10.0,
        margin_used_usdt=1000.0,
        liquidation_price=9000.0,
        updated_at=datetime.now(UTC),
    )


def _patch_api_lifespan(monkeypatch) -> None:
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


def _load_compose_text() -> str:
    return Path(__file__).resolve().parents[2].joinpath("docker-compose.yml").read_text(
        encoding="utf-8"
    )


@pytest.mark.asyncio
async def test_int_001_01_stream_ativo_com_atualizacao_continua() -> None:
    """INT_001_01: stream ativo com atualização contínua na Binance Futures."""
    client = await _build_client_or_skip()
    stream = PositionStream(client, keepalive_interval=1800)

    try:
        await _start_stream_or_skip(stream)

        status_samples: list[str] = []
        started_at = monotonic()
        while monotonic() - started_at < 2.2:
            status_samples.append(stream.get_status())
            await asyncio.sleep(0.55)

        assert status_samples
        assert all(status == "online" for status in status_samples)

        positions = stream.get_positions()
        assert isinstance(positions, list)
    finally:
        await stream.stop()
        await client.close()


@pytest.mark.asyncio
async def test_int_001_02_queda_de_stream_com_fallback_automatico() -> None:
    """INT_001_02: queda de stream deve acionar fallback e restauração na Binance Futures."""
    client = await _build_client_or_skip()
    stream = PositionStream(client, keepalive_interval=1800)
    updater = AdaptiveUpdater(
        monitor_interval=0.2,
        fast_poll_interval=0.5,
        stable_poll_interval=1.0,
        adaptive_window_seconds=3.0,
        stale_window_seconds=1.0,
    )

    try:
        await _start_stream_or_skip(stream)
        await updater.start(stream)

        await stream._set_status("degraded")
        await _wait_until(lambda: stream.get_status() == "online")

        assert stream.get_status() == "online"
        assert isinstance(stream.get_positions(), list)
    finally:
        await updater.stop()
        await stream.stop()
        await client.close()


@pytest.mark.asyncio
async def test_int_001_03_reconciliacao_apos_divergencia_de_cache() -> None:
    """INT_001_03: reconciliação deve sobrescrever cache divergente com snapshot Binance Futures."""
    client = await _build_client_or_skip()
    stream = PositionStream(client, keepalive_interval=1800)
    updater = AdaptiveUpdater(
        monitor_interval=0.2,
        fast_poll_interval=0.5,
        stable_poll_interval=1.0,
        adaptive_window_seconds=3.0,
        stale_window_seconds=1.0,
    )

    try:
        await _start_stream_or_skip(stream)
        await updater.start(stream)

        # Injeta divergência local para validar reconciliação com fonte autoritativa.
        stream._positions = {"FAKEUSDT": _build_divergent_position()}

        await stream._set_status("degraded")
        await _wait_until(lambda: stream.get_status() == "online")

        symbols = {position.symbol for position in stream.get_positions()}
        assert "FAKEUSDT" not in symbols
    finally:
        await updater.stop()
        await stream.stop()
        await client.close()


def test_int_002_01_compose_expoe_dashboard_api_localmente() -> None:
    """INT_002_01: o compose deve declarar o serviço dashboard-api com binding local."""
    compose_text = _load_compose_text()

    assert "dashboard-api:" in compose_text
    assert "dockerfile: docker/Dockerfile.api" in compose_text
    assert "127.0.0.1:8080:8080" in compose_text
    assert "env_file:" in compose_text
    assert "phicube-net" in compose_text
    assert "mongo:" in compose_text


def test_int_002_02_api_serva_frontend_e_snapshot_cached(monkeypatch) -> None:
    """INT_002_02: a API deve servir o frontend e responder snapshot cached localmente."""
    _patch_api_lifespan(monkeypatch)

    app = api_main.create_app()
    with TestClient(app) as client:
        cached_position = _make_spec_002_position(
            symbol="BTCUSDT",
            updated_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
        )
        client.app.state.position_stream = _FakeStream(
            positions=[cached_position],
            status="cached",
        )

        root_response = client.get("/")
        health_response = client.get("/health")
        positions_response = client.get("/positions")

    assert root_response.status_code == 200
    assert "Consulta de Posições" in root_response.text
    assert health_response.status_code == 200
    assert health_response.json() == {"status": "cached"}
    assert positions_response.status_code == 200
    assert positions_response.json()["status"] == "cached"
    assert positions_response.json()["positions"][0]["symbol"] == "BTCUSDT"


def test_int_002_03_websocket_entrega_snapshot_e_broadcast_local(monkeypatch) -> None:
    """INT_002_03: o WebSocket deve entregar snapshot inicial e broadcast local."""
    _patch_api_lifespan(monkeypatch)

    app = api_main.create_app()
    with TestClient(app) as client:
        stream = _FakeStream(
            positions=[
                _make_spec_002_position(
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

            stream._positions = [
                _make_spec_002_position(
                    symbol="ETHUSDT",
                    updated_at=datetime(2026, 5, 1, 12, 31, tzinfo=UTC),
                )
            ]
            assert stream.on_update is not None
            client.portal.call(stream.on_update, stream)
            broadcast_payload = websocket.receive_json()

    assert broadcast_payload["status"] == "online"
    assert broadcast_payload["positions"][0]["symbol"] == "ETHUSDT"
