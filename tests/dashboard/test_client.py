"""Testes unitários para DashboardClient — validação de permissões READ_ONLY."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.dashboard.client import DashboardClient, DashboardClientError

# ─── Fixtures ────────────────────────────────────────────────────────────────


def _make_settings(
    *,
    dashboard_api_key: str = "test_key",
    dashboard_api_secret: str = "test_secret",
    binance_testnet: bool = True,
) -> MagicMock:
    """Cria um mock de Settings com os campos necessários."""
    settings = MagicMock()
    settings.dashboard_api_key = dashboard_api_key
    settings.dashboard_api_secret = dashboard_api_secret
    settings.binance_testnet = binance_testnet
    return settings


# ─── Testes de validação de permissões ───────────────────────────────────────


@pytest.mark.asyncio
async def test_connect_rejeita_key_com_permissao_de_trade() -> None:
    """Key com enableSpotAndMarginTrading=True deve lançar DashboardClientError."""
    settings = _make_settings()
    client = DashboardClient(settings)

    with patch.object(client._exchange, "load_markets", new_callable=AsyncMock):
        with patch.object(
            client,
            "_fetch_api_restrictions",
            new_callable=AsyncMock,
            return_value={"enableSpotAndMarginTrading": True, "enableFutures": False},
        ):
            with pytest.raises(DashboardClientError, match="não é READ_ONLY"):
                await client.connect()


@pytest.mark.asyncio
async def test_connect_rejeita_key_com_permissao_de_futures() -> None:
    """Key com enableFutures=True deve lançar DashboardClientError."""
    settings = _make_settings()
    client = DashboardClient(settings)

    with patch.object(client._exchange, "load_markets", new_callable=AsyncMock):
        with patch.object(
            client,
            "_fetch_api_restrictions",
            new_callable=AsyncMock,
            return_value={"enableSpotAndMarginTrading": False, "enableFutures": True},
        ):
            with pytest.raises(DashboardClientError, match="não é READ_ONLY"):
                await client.connect()


@pytest.mark.asyncio
async def test_connect_aceita_key_readonly() -> None:
    """Key com flags de spot/margin e futures desabilitadas deve conectar sem erro."""
    settings = _make_settings()
    client = DashboardClient(settings)

    with patch.object(client._exchange, "load_markets", new_callable=AsyncMock):
        with patch.object(
            client,
            "_fetch_api_restrictions",
            new_callable=AsyncMock,
            return_value={"enableSpotAndMarginTrading": False, "enableFutures": False},
        ):
            await client.connect()  # Não deve lançar exceção


@pytest.mark.asyncio
async def test_connect_rejeita_payload_vazio_de_permissoes() -> None:
    """Payload vazio deve bloquear a inicialização por validação inconclusiva."""
    settings = _make_settings()
    client = DashboardClient(settings)

    with patch.object(client._exchange, "load_markets", new_callable=AsyncMock):
        with patch.object(
            client,
            "_fetch_api_restrictions",
            new_callable=AsyncMock,
            return_value={},
        ):
            with pytest.raises(DashboardClientError, match="payload incompleto"):
                await client.connect()


@pytest.mark.asyncio
async def test_connect_rejeita_payload_parcial_de_permissoes() -> None:
    """Payload parcial deve bloquear a inicialização por validação inconclusiva."""
    settings = _make_settings()
    client = DashboardClient(settings)

    with patch.object(client._exchange, "load_markets", new_callable=AsyncMock):
        with patch.object(
            client,
            "_fetch_api_restrictions",
            new_callable=AsyncMock,
            return_value={"enableFutures": False},
        ):
            with pytest.raises(DashboardClientError, match="payload incompleto"):
                await client.connect()


@pytest.mark.asyncio
async def test_connect_lanca_erro_em_falha_de_autenticacao() -> None:
    """Falha de autenticação/SDK deve propagar como DashboardClientError."""
    settings = _make_settings()
    client = DashboardClient(settings)

    with patch.object(client._exchange, "load_markets", new_callable=AsyncMock):
        with patch.object(
            client,
            "_fetch_api_restrictions",
            new_callable=AsyncMock,
            side_effect=DashboardClientError("Falha de autenticação ao consultar SDK"),
        ):
            with pytest.raises(DashboardClientError, match="Falha de autenticação"):
                await client.connect()


# ─── Testes de isolamento de instância ───────────────────────────────────────


def test_dashboard_client_nao_compartilha_instancia_com_binance_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DashboardClient deve instanciar exchange próprio — nunca reutilizar."""
    from src.config.settings import Settings
    from src.exchange.binance_client import BinanceClient

    monkeypatch.setenv("BINANCE_API_KEY", "bot_key")
    monkeypatch.setenv("BINANCE_API_SECRET", "bot_secret")
    monkeypatch.setenv("DASHBOARD_API_KEY", "dash_key")
    monkeypatch.setenv("DASHBOARD_API_SECRET", "dash_secret")

    with patch.dict(Settings.model_config, {"env_file": None}):
        settings = cast(Any, Settings)()

    bot_client = BinanceClient(settings)
    dash_client = DashboardClient(settings)

    assert (
        bot_client._exchange is not dash_client._exchange
    ), "BinanceClient e DashboardClient não devem compartilhar a mesma instância ccxt"
