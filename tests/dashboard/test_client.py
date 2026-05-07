"""Testes unitários para DashboardClient — validação de permissões READ_ONLY."""

from __future__ import annotations

import sys
from types import ModuleType
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

    with patch.object(client, "_sync_exchange_clock", new_callable=AsyncMock):
        with patch.object(client, "_sync_sdk_clock", new_callable=AsyncMock):
            with patch.object(client._exchange, "load_markets", new_callable=AsyncMock):
                with patch.object(client, "_validate_futures_access", new_callable=AsyncMock):
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

    with patch.object(client, "_sync_exchange_clock", new_callable=AsyncMock):
        with patch.object(client, "_sync_sdk_clock", new_callable=AsyncMock):
            with patch.object(client._exchange, "load_markets", new_callable=AsyncMock):
                with patch.object(client, "_validate_futures_access", new_callable=AsyncMock):
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

    with patch.object(client, "_sync_exchange_clock", new_callable=AsyncMock):
        with patch.object(client, "_sync_sdk_clock", new_callable=AsyncMock):
            with patch.object(client._exchange, "load_markets", new_callable=AsyncMock):
                with patch.object(client, "_validate_futures_access", new_callable=AsyncMock):
                    with patch.object(
                        client,
                        "_fetch_api_restrictions",
                        new_callable=AsyncMock,
                        return_value={"enableSpotAndMarginTrading": False, "enableFutures": False},
                    ):
                        await client.connect()  # Não deve lançar exceção


@pytest.mark.asyncio
async def test_connect_ignora_falha_de_sincronismo_de_mercados() -> None:
    """Falha no load_markets não deve bloquear a validação READ_ONLY."""
    settings = _make_settings()
    client = DashboardClient(settings)

    with patch.object(client, "_sync_exchange_clock", new_callable=AsyncMock):
        with patch.object(client, "_sync_sdk_clock", new_callable=AsyncMock):
            with patch.object(
                client._exchange,
                "load_markets",
                new_callable=AsyncMock,
                side_effect=RuntimeError("timestamp skew"),
            ):
                with patch.object(client, "_validate_futures_access", new_callable=AsyncMock):
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

    with patch.object(client, "_sync_exchange_clock", new_callable=AsyncMock):
        with patch.object(client, "_sync_sdk_clock", new_callable=AsyncMock):
            with patch.object(client._exchange, "load_markets", new_callable=AsyncMock):
                with patch.object(client, "_validate_futures_access", new_callable=AsyncMock):
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

    with patch.object(client, "_sync_exchange_clock", new_callable=AsyncMock):
        with patch.object(client, "_sync_sdk_clock", new_callable=AsyncMock):
            with patch.object(client._exchange, "load_markets", new_callable=AsyncMock):
                with patch.object(client, "_validate_futures_access", new_callable=AsyncMock):
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

    with patch.object(client, "_sync_exchange_clock", new_callable=AsyncMock):
        with patch.object(client, "_sync_sdk_clock", new_callable=AsyncMock):
            with patch.object(client._exchange, "load_markets", new_callable=AsyncMock):
                with patch.object(client, "_validate_futures_access", new_callable=AsyncMock):
                    with patch.object(
                        client,
                        "_fetch_api_restrictions",
                        new_callable=AsyncMock,
                        side_effect=DashboardClientError("Falha de autenticação ao consultar SDK"),
                    ):
                        with pytest.raises(DashboardClientError, match="Falha de autenticação"):
                            await client.connect()


def test_classifica_erro_401_2015_como_auth_issue_mainnet() -> None:
    settings = _make_settings(binance_testnet=False)
    client = DashboardClient(settings)

    msg = (
        "Falha ao executar 'new_listen_key': "
        "(401, -2015, 'Invalid API-key, IP, or permissions for action')"
    )
    issue = client._classify_auth_issue(DashboardClientError(msg))

    assert issue is not None
    assert issue.reason in {
        "invalid_key_or_secret",
        "ip_not_whitelisted",
        "missing_futures_permission",
    }


def test_classifica_erro_401_2015_como_env_mismatch_no_testnet() -> None:
    settings = _make_settings(binance_testnet=True)
    client = DashboardClient(settings)

    msg = (
        "Falha ao executar 'new_listen_key': "
        "(401, -2015, 'Invalid API-key, IP, or permissions for action')"
    )
    issue = client._classify_auth_issue(DashboardClientError(msg))

    assert issue is not None
    assert issue.reason in {
        "env_mismatch_testnet_mainnet",
        "ip_not_whitelisted",
        "missing_futures_permission",
    }


@pytest.mark.asyncio
async def test_sync_sdk_clock_ajusta_timestamp_global() -> None:
    """O relógio do SDK deve ser sincronizado com o serverTime da Binance."""
    settings = _make_settings()
    client = DashboardClient(settings)

    fake_binance = ModuleType("binance")
    fake_api = ModuleType("binance.api")

    def _original_timestamp() -> int:
        return 0

    fake_api.get_timestamp = _original_timestamp  # type: ignore[attr-defined]
    fake_binance.api = fake_api  # type: ignore[attr-defined]
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setitem(sys.modules, "binance", fake_binance)
    monkeypatch.setitem(sys.modules, "binance.api", fake_api)

    try:
        with patch.object(
            client,
            "_call_um_futures",
            new_callable=AsyncMock,
            return_value={"serverTime": 123456},
        ):
            with patch("src.dashboard.client.time.time", return_value=100.0):
                await client._sync_sdk_clock()

        with patch("src.dashboard.client.time.time", return_value=100.0):
            assert fake_api.get_timestamp() == 123456

        client._restore_sdk_timestamp()
        with patch("src.dashboard.client.time.time", return_value=100.0):
            assert fake_api.get_timestamp() == 0
    finally:
        monkeypatch.undo()


@pytest.mark.asyncio
async def test_fetch_open_positions_recae_para_sdk_quando_ccxt_falha() -> None:
    """Se o ccxt falhar, o cliente deve tentar obter as posições via SDK."""
    settings = _make_settings()
    client = DashboardClient(settings)

    sdk_payload = [
        {
            "symbol": "BTCUSDT",
            "positionAmt": "0.5",
            "entryPrice": "95000",
            "markPrice": "96000",
            "unRealizedProfit": "250",
            "liquidationPrice": "87000",
        }
    ]

    with patch.object(
        client._exchange,
        "fetch_positions",
        new_callable=AsyncMock,
        side_effect=RuntimeError("ccxt indisponivel"),
    ):
        with patch.object(
            client,
            "_call_um_futures",
            new_callable=AsyncMock,
            return_value=sdk_payload,
        ):
            positions = await client.fetch_open_positions()

    assert positions == sdk_payload


@pytest.mark.asyncio
async def test_fetch_position_risk_recae_para_sdk_quando_ccxt_falha() -> None:
    """O snapshot inicial do painel deve tentar o SDK antes de abandonar a leitura."""
    settings = _make_settings()
    client = DashboardClient(settings)

    sdk_payload = [
        {
            "symbol": "BTCUSDT",
            "positionAmt": "0.5",
            "entryPrice": "95000",
            "markPrice": "96000",
            "unRealizedProfit": "250",
            "liquidationPrice": "87000",
        }
    ]

    with patch.object(
        client,
        "_call_um_futures",
        new_callable=AsyncMock,
        return_value=sdk_payload,
    ):
        positions = await client.fetch_position_risk()

    assert positions == sdk_payload


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
