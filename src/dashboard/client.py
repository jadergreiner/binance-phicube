"""Cliente ccxt async READ_ONLY dedicado ao painel de posições.

Este cliente é isolado do cliente do bot (`BinanceClient`) e utiliza
credenciais separadas (`DASHBOARD_API_KEY` / `DASHBOARD_API_SECRET`).
A inicialização valida explicitamente que a Key não possui permissão de
trade, lançando `DashboardClientError` caso contrário.
"""

from __future__ import annotations

import asyncio
import time
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
            "adjustForTimeDifference": True,
            "enableRateLimit": True,
        }

        # Instância exclusiva — não compartilhada com BinanceClient
        # Demo Trading (substituto do Testnet descontinuado) usa endpoints de produção
        self._exchange: ccxt.binanceusdm = ccxt.binanceusdm(params)
        self._settings = settings
        self._um_futures_client: Any | None = None
        self._sdk_get_timestamp_original: Any | None = None
        self._sdk_clock_offset_ms: int | None = None

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Carrega mercados e valida permissões da API Key."""
        await self._sync_exchange_clock()
        await self._sync_sdk_clock()

        try:
            await self._exchange.load_markets()
        except Exception as exc:
            logger.warning("dashboard_client_load_markets_failed", error=str(exc))
        await self._validate_readonly_permissions()
        logger.info("dashboard_client_connected", testnet=self._settings.binance_testnet)

    async def close(self) -> None:
        """Fecha a conexão com a exchange."""
        self._restore_sdk_timestamp()
        await self._exchange.close()
        logger.info("dashboard_client_closed")

    # ─── Validação de permissões ───────────────────────────────────────────────

    async def _fetch_api_restrictions(self) -> dict[str, Any]:
        """Consulta restrições da API Key via SDK oficial da Binance."""
        try:
            from binance.spot import Spot
        except ImportError as exc:
            raise DashboardClientError(
                "Dependência ausente para validar permissões da Dashboard API Key. "
                "Instale `binance-connector`."
            ) from exc

        spot_client = Spot(
            api_key=self._settings.dashboard_api_key,
            api_secret=self._settings.dashboard_api_secret,
        )

        try:
            response = await asyncio.to_thread(spot_client.api_restrictions)
        except Exception as exc:
            raise DashboardClientError(
                "Falha ao consultar restrições da Dashboard API Key via SDK oficial da Binance."
            ) from exc

        if not isinstance(response, dict):
            raise DashboardClientError(
                "Resposta inválida ao consultar restrições da Dashboard API Key via SDK oficial da "
                "Binance."
            )

        return response

    def _get_um_futures_client(self) -> Any:
        if self._um_futures_client is not None:
            return self._um_futures_client

        try:
            from binance.um_futures import UMFutures
        except ImportError as exc:
            raise DashboardClientError(
                "Dependência ausente para operações de Futures da Dashboard API Key. "
                "Instale `binance-futures-connector`."
            ) from exc

        self._um_futures_client = UMFutures(
            key=self._settings.dashboard_api_key,
            secret=self._settings.dashboard_api_secret,
        )
        return self._um_futures_client

    async def _sync_exchange_clock(self) -> None:
        try:
            await self._exchange.load_time_difference()
        except Exception as exc:
            logger.warning("dashboard_client_load_time_difference_failed", error=str(exc))

    async def _sync_sdk_clock(self) -> None:
        try:
            response = await self._call_um_futures("time")
        except Exception as exc:
            logger.warning("dashboard_client_sdk_clock_sync_failed", error=str(exc))
            return

        if not isinstance(response, dict):
            logger.warning("dashboard_client_sdk_clock_sync_failed", error="Resposta inválida do endpoint de tempo")
            return

        server_time = response.get("serverTime")
        if server_time is None:
            logger.warning("dashboard_client_sdk_clock_sync_failed", error="Servidor não retornou serverTime")
            return

        try:
            from binance import api as binance_api
        except ImportError:
            logger.warning(
                "dashboard_client_sdk_clock_sync_failed",
                error="Módulo binance.api indisponível para ajustar o timestamp",
            )
            return

        offset_ms = int(server_time) - int(time.time() * 1000)
        self._sdk_clock_offset_ms = offset_ms

        if self._sdk_get_timestamp_original is None:
            self._sdk_get_timestamp_original = binance_api.get_timestamp

        def _adjusted_get_timestamp() -> int:
            return int(time.time() * 1000) + offset_ms

        binance_api.get_timestamp = _adjusted_get_timestamp
        logger.info(
            "dashboard_client_sdk_clock_synchronized",
            server_time=int(server_time),
            offset_ms=offset_ms,
        )

    def _restore_sdk_timestamp(self) -> None:
        if self._sdk_get_timestamp_original is None:
            return

        try:
            from binance import api as binance_api
        except ImportError:
            self._sdk_get_timestamp_original = None
            self._sdk_clock_offset_ms = None
            return

        binance_api.get_timestamp = self._sdk_get_timestamp_original
        self._sdk_get_timestamp_original = None
        self._sdk_clock_offset_ms = None

    async def _call_um_futures(self, method_name: str, **params: Any) -> Any:
        client = self._get_um_futures_client()
        method = getattr(client, method_name, None)
        if method is None:
            raise DashboardClientError(
                f"SDK Binance Futures sem suporte ao método '{method_name}' neste ambiente."
            )

        try:
            return await asyncio.to_thread(method, **params)
        except Exception as exc:
            raise DashboardClientError(
                f"Falha ao executar '{method_name}' no SDK Binance Futures: {exc}"
            ) from exc

    async def fetch_position_risk(self, *, symbol: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if symbol:
            params["symbol"] = symbol

        try:
            response = await self._call_um_futures("get_position_risk", **params)
            payload = response if isinstance(response, list) else [response]
            positions = [raw for raw in payload if isinstance(raw, dict)]
            if positions:
                return positions
        except Exception as exc:
            logger.warning("dashboard_client_fetch_position_risk_sdk_failed", error=str(exc))

        try:
            positions = await self._exchange.fetch_positions()
        except Exception as exc:
            logger.warning("dashboard_client_fetch_position_risk_ccxt_failed", error=str(exc))
            return []

        payload = positions if isinstance(positions, list) else [positions]
        filtered_positions = [raw for raw in payload if isinstance(raw, dict)]
        if symbol:
            filtered_positions = [raw for raw in filtered_positions if raw.get("symbol") == symbol]

        return filtered_positions

    async def create_listen_key(self) -> str:
        response = await self._call_um_futures("new_listen_key")
        if not isinstance(response, dict):
            raise DashboardClientError("Resposta inválida ao criar listenKey da Binance Futures")

        listen_key = response.get("listenKey")
        if not listen_key:
            raise DashboardClientError("Binance não retornou listenKey válido para o painel")

        return str(listen_key)

    async def renew_listen_key(self, listen_key: str) -> None:
        await self._call_um_futures("renew_listen_key", listenKey=listen_key)

    async def delete_listen_key(self, listen_key: str) -> None:
        await self._call_um_futures("close_listen_key", listenKey=listen_key)

    def get_last_response_headers(self) -> dict[str, Any]:
        # O SDK oficial não expõe headers HTTP de forma estável para controle de rate limit.
        return {}

    async def _validate_readonly_permissions(self) -> None:
        """Verifica que a Key NÃO possui permissão de trade.

        Obtém as restrições da API Key via SDK oficial da Binance. Se a Key
        possuir permissão de negociação spot/margin ou futuros, lança
        `DashboardClientError`.

        Raises:
            DashboardClientError: se a Key tiver permissão de trade ou se não
                for possível verificar as permissões.
        """
        response = await self._fetch_api_restrictions()

        required_fields = {"enableFutures", "enableSpotAndMarginTrading"}
        if not required_fields.issubset(response.keys()):
            raise DashboardClientError(
                "Permissões não puderam ser verificadas: payload incompleto da API"
            )

        enable_futures: bool = bool(response["enableFutures"])
        enable_spot_margin_trading: bool = bool(response["enableSpotAndMarginTrading"])

        if enable_futures or enable_spot_margin_trading:
            raise DashboardClientError(
                "A Dashboard API Key não é READ_ONLY (enableFutures="
                f"{enable_futures}, "
                "enableSpotAndMarginTrading="
                f"{enable_spot_margin_trading}). "
                "Utilize uma Key exclusivamente READ_ONLY para o painel."
            )

        logger.info(
            "dashboard_api_key_readonly_validated",
            enable_futures=enable_futures,
            enable_spot_margin_trading=enable_spot_margin_trading,
        )

    # ─── Dados de mercado ─────────────────────────────────────────────────────

    async def fetch_open_positions(self) -> list[dict[str, Any]]:
        """Retorna todas as posições abertas (contratos != 0)."""
        try:
            positions: list[dict[str, Any]] = await self._exchange.fetch_positions()
            return [p for p in positions if float(p.get("contracts", 0)) != 0]
        except Exception as exc:
            logger.warning("dashboard_client_fetch_positions_ccxt_failed", error=str(exc))

        raw_positions = await self._call_um_futures("get_position_risk")
        payload = raw_positions if isinstance(raw_positions, list) else [raw_positions]

        positions: list[dict[str, Any]] = []
        for raw_position in payload:
            if not isinstance(raw_position, dict):
                continue

            quantity = raw_position.get("positionAmt")
            try:
                if float(quantity) == 0:
                    continue
            except (TypeError, ValueError):
                continue

            positions.append(raw_position)

        return positions

    async def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        """Retorna o ticker (preço atual) de um símbolo."""
        return await self._exchange.fetch_ticker(symbol)

    async def fetch_balance(self) -> dict[str, Any]:
        """Retorna o saldo da carteira de futuros (READ_ONLY)."""
        return await self._exchange.fetch_balance({"type": "future"})
