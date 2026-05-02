"""Cliente ccxt async READ_ONLY dedicado ao painel de posições.

Este cliente é isolado do cliente do bot (`BinanceClient`) e utiliza
credenciais separadas (`DASHBOARD_API_KEY` / `DASHBOARD_API_SECRET`).
A inicialização valida explicitamente que a Key não possui permissão de
trade, lançando `DashboardClientError` caso contrário.
"""

from __future__ import annotations

from typing import Any

import ccxt.async_support as ccxt

from src.config.settings import Settings
from src.monitoring.logger import get_logger

logger = get_logger(__name__)


class DashboardClientError(Exception):
    """Erro específico do cliente do painel."""


class DashboardClient:
    """Cliente ccxt async READ_ONLY para o painel de posições em tempo real.

    Instancia um exchange `binanceusdm` exclusivo — nunca compartilha
    instância com o `BinanceClient` do bot.
    """

    def __init__(self, settings: Settings) -> None:
        params: dict[str, Any] = {
            "apiKey": settings.dashboard_api_key,
            "secret": settings.dashboard_api_secret,
            "options": {"defaultType": "future"},
            "enableRateLimit": True,
        }

        # Instância exclusiva — não compartilhada com BinanceClient
        # Demo Trading (substituto do Testnet descontinuado) usa endpoints de produção
        self._exchange: ccxt.binanceusdm = ccxt.binanceusdm(params)
        self._settings = settings

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Carrega mercados e valida permissões da API Key."""
        await self._exchange.load_markets()
        await self._validate_readonly_permissions()
        logger.info("dashboard_client_connected", testnet=self._settings.binance_testnet)

    async def close(self) -> None:
        """Fecha a conexão com a exchange."""
        await self._exchange.close()
        logger.info("dashboard_client_closed")

    # ─── Validação de permissões ───────────────────────────────────────────────

    async def _validate_readonly_permissions(self) -> None:
        """Verifica que a Key NÃO possui permissão de trade.

        Obtém as permissões da API Key via endpoint `/fapi/v1/apiTradingStatus`
        ou equivalente disponível no ccxt. Se a Key possuir permissão de
        negociação (`enableTrading=True`), lança `DashboardClientError`.

        Raises:
            DashboardClientError: se a Key tiver permissão de trade ou se não
                for possível verificar as permissões.
        """
        try:
            # fetch_api_key_permissions está disponível na Binance Futures
            response: dict[str, Any] = await self._exchange.fetch_api_key_permissions()
        except ccxt.AuthenticationError as exc:
            raise DashboardClientError(
                "Falha de autenticação ao validar permissões da Dashboard API Key. "
                "Verifique DASHBOARD_API_KEY e DASHBOARD_API_SECRET."
            ) from exc
        except ccxt.NotSupported as exc:
            logger.warning(
                "dashboard_permission_check_not_supported",
                message=(
                    "Inicializacao bloqueada: nao foi possivel verificar a permissao "
                    "READ_ONLY da Dashboard API Key."
                ),
            )
            raise DashboardClientError(
                "Inicializacao bloqueada: nao foi possivel verificar a permissao READ_ONLY da "
                "Dashboard API Key porque o endpoint de validacao nao e suportado neste ambiente."
            ) from exc
        except Exception as exc:
            raise DashboardClientError(
                f"Erro inesperado ao verificar permissões da Dashboard API Key: {exc}"
            ) from exc

        required_fields = {"enableTrading", "enableFutures"}
        if not required_fields.issubset(response.keys()):
            raise DashboardClientError(
                "Permissões não puderam ser verificadas: payload incompleto da API"
            )

        enable_trading: bool = response["enableTrading"]
        enable_futures: bool = response["enableFutures"]

        if enable_trading or enable_futures:
            raise DashboardClientError(
                "A Dashboard API Key possui permissão de trade (enableTrading="
                f"{enable_trading}, enableFutures={enable_futures}). "
                "Utilize uma Key exclusivamente READ_ONLY para o painel."
            )

        logger.info(
            "dashboard_api_key_readonly_validated",
            enable_trading=enable_trading,
            enable_futures=enable_futures,
        )

    # ─── Dados de mercado ─────────────────────────────────────────────────────

    async def fetch_open_positions(self) -> list[dict[str, Any]]:
        """Retorna todas as posições abertas (contratos != 0)."""
        positions: list[dict[str, Any]] = await self._exchange.fetch_positions()
        return [p for p in positions if float(p.get("contracts", 0)) != 0]

    async def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        """Retorna o ticker (preço atual) de um símbolo."""
        return await self._exchange.fetch_ticker(symbol)

    async def fetch_balance(self) -> dict[str, Any]:
        """Retorna o saldo da carteira de futuros (READ_ONLY)."""
        return await self._exchange.fetch_balance({"type": "future"})
