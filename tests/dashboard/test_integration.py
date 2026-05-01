from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic

import pytest

from src.dashboard.client import DashboardClient
from src.dashboard.models import PositionView
from src.dashboard.stream import PositionStream
from src.dashboard.updater import AdaptiveUpdater


@dataclass(slots=True)
class _IntegrationSettings:
    dashboard_api_key: str
    dashboard_api_secret: str
    binance_testnet: bool = True


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _build_integration_settings_or_skip() -> _IntegrationSettings:
    api_key = os.getenv("DASHBOARD_API_KEY", "").strip()
    api_secret = os.getenv("DASHBOARD_API_SECRET", "").strip()

    if not api_key or not api_secret:
        pytest.skip(
            "INT_001 bloqueado: variáveis DASHBOARD_API_KEY/DASHBOARD_API_SECRET ausentes. "
            "Configure credenciais da Binance Testnet para executar integração real."
        )

    testnet_env = os.getenv("BINANCE_TESTNET", "true")
    if not _is_truthy(testnet_env):
        pytest.skip(
            "INT_001 bloqueado por segurança: BINANCE_TESTNET precisa estar habilitado "
            "(true/1/yes/on). Execução em produção não é permitida."
        )

    return _IntegrationSettings(
        dashboard_api_key=api_key,
        dashboard_api_secret=api_secret,
        binance_testnet=True,
    )


async def _build_client_or_skip() -> DashboardClient:
    settings = _build_integration_settings_or_skip()
    client = DashboardClient(settings)

    try:
        await asyncio.wait_for(client._exchange.fapiPrivateV2GetPositionRisk(), timeout=20)
    except Exception as exc:
        await client.close()
        pytest.skip(
            "INT_001 bloqueado: não foi possível acessar a Binance Testnet "
            f"com as credenciais informadas ({exc!r})."
        )

    return client


async def _start_stream_or_skip(stream: PositionStream) -> None:
    await asyncio.wait_for(stream.start(), timeout=30)
    if stream.get_status() != "online":
        await stream.stop(status="offline")
        pytest.skip(
            "INT_001 bloqueado: stream não ficou online na Testnet após inicialização. "
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


@pytest.mark.asyncio
async def test_int_001_01_stream_ativo_com_atualizacao_continua() -> None:
    """INT_001_01: stream ativo com atualização contínua na Testnet."""
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
    """INT_001_02: queda de stream deve acionar fallback e restauração."""
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
    """INT_001_03: reconciliação deve sobrescrever cache divergente com snapshot Binance."""
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
