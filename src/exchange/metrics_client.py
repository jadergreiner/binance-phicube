"""
Decorator de métricas para BinanceClient — não invasivo, thread-safe.

Aplica o padrão Decorator: envolve o BinanceClient original sem modificá-lo,
adicionando métricas de latência, contagem de requests e tratamento de erros.

Uso:
    from src.exchange.binance_client import BinanceClient
    from src.exchange.metrics_client import MetricsBinanceClient

    raw_client = BinanceClient(settings)
    client = MetricsBinanceClient(raw_client)

    # Usa exatamente a mesma interface do BinanceClient
    await client.connect()
    df = await client.fetch_ohlcv_with_retry("BTCUSDT", "15m")
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import pandas as pd

from src.monitoring.logger import get_logger
from src.monitoring.metrics import (
    observe_candle_latency,
    record_api_request,
    record_error,
)

if TYPE_CHECKING:
    from src.exchange.binance_client import BinanceClient

logger = get_logger(__name__)


class MetricsBinanceClient:
    """
    Decorador de métricas para BinanceClient.

    Implementa a mesma interface pública do BinanceClient e delega todas as
    chamadas para o cliente wrapped, adicionando métricas de Prometheus
    de forma não invasiva (padrão Decorator).

    Métricas coletadas:
    - api_requests_total: contador por endpoint e status (success/error)
    - candle_latency_seconds: histogram para fetch_ohlcv
    - errors_total: contador de erros por módulo

    Nota: métodos sync (get_quantity_precision, round_quantity, round_price)
    não são instrumentados porque são muito baratos e só usam dados em memória.
    """

    def __init__(self, wrapped_client: BinanceClient) -> None:
        self._wrapped = wrapped_client

    # ─── Lifecycle ──────────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Delega para wrapped.connect() sem métricas (uma vez no startup)."""
        await self._wrapped.connect()

    async def close(self) -> None:
        """Delega para wrapped.close() sem métricas (uma vez no shutdown)."""
        await self._wrapped.close()

    # ─── Market Data ────────────────────────────────────────────────────────────

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 200,
        since: int | None = None,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV com métrica de latência.

        Nota: Na maioria dos casos você quer fetch_ohlcv_with_retry().
        Este método é exposto para compatibilidade completa da interface.
        """
        start = time.time()
        endpoint = "fetch_ohlcv"
        try:
            result = await self._wrapped.fetch_ohlcv(symbol, timeframe, limit, since)
            latency = time.time() - start
            observe_candle_latency(symbol, latency)
            record_api_request(endpoint, "success")
            return result
        except Exception as exc:
            latency = time.time() - start
            observe_candle_latency(symbol, latency)
            record_api_request(endpoint, "error")
            record_error("exchange", type(exc).__name__)
            raise

    async def fetch_ohlcv_with_retry(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 200,
        retries: int | None = None,
        base_delay: float | None = None,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV com retry + métricas.

        Este é o método usado pelo TradingMonitor no loop principal.
        Mede latência total (incluindo retries) e atualiza candle_latency_seconds.
        """
        start = time.time()
        endpoint = "fetch_ohlcv"
        try:
            result = await self._wrapped.fetch_ohlcv_with_retry(
                symbol, timeframe, limit, retries, base_delay
            )
            latency = time.time() - start
            observe_candle_latency(symbol, latency)
            record_api_request(endpoint, "success")
            return result
        except Exception as exc:
            latency = time.time() - start
            observe_candle_latency(symbol, latency)
            record_api_request(endpoint, "error")
            record_error("exchange", type(exc).__name__)
            raise

    async def fetch_balance(self) -> dict[str, Any]:
        return await self._instrumented_async(
            "fetch_balance",
            lambda: self._wrapped.fetch_balance(),
        )

    async def fetch_usdt_balance(self) -> float:
        return await self._instrumented_async(
            "fetch_balance",
            lambda: self._wrapped.fetch_usdt_balance(),
        )

    async def fetch_open_positions(self) -> list[dict[str, Any]]:
        return await self._instrumented_async(
            "fetch_positions",
            lambda: self._wrapped.fetch_open_positions(),
        )

    async def fetch_position_risk(
        self, *, symbol: str | None = None
    ) -> list[dict[str, Any]]:
        return await self._instrumented_async(
            "fetch_positions",
            lambda: self._wrapped.fetch_position_risk(symbol=symbol),
        )

    async def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        return await self._instrumented_async(
            "fetch_ticker",
            lambda: self._wrapped.fetch_ticker(symbol),
        )

    async def validate_market_liquidity(
        self,
        symbol: str,
        min_volume: float = 500000.0,
        min_oi: float = 200000.0,
    ) -> None:
        return await self._instrumented_async(
            "validate_liquidity",
            lambda: self._wrapped.validate_market_liquidity(
                symbol, min_volume, min_oi
            ),
        )

    async def fetch_quantity_precision_map(
        self, symbols: list[str]
    ) -> dict[str, int]:
        return await self._instrumented_async(
            "fetch_markets",
            lambda: self._wrapped.fetch_quantity_precision_map(symbols),
        )

    # ─── Order Management ───────────────────────────────────────────────────────

    async def set_leverage(self, symbol: str, leverage: int) -> None:
        return await self._instrumented_async(
            "set_leverage",
            lambda: self._wrapped.set_leverage(symbol, leverage),
        )

    async def set_margin_mode(self, symbol: str, mode: str = "isolated") -> None:
        return await self._instrumented_async(
            "set_margin_mode",
            lambda: self._wrapped.set_margin_mode(symbol, mode),
        )

    async def create_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._instrumented_async(
            "create_market_order",
            lambda: self._wrapped.create_market_order(symbol, side, quantity, params),
        )

    async def create_stop_loss_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
    ) -> dict[str, Any]:
        return await self._instrumented_async(
            "create_stop_loss_order",
            lambda: self._wrapped.create_stop_loss_order(symbol, side, quantity, stop_price),
        )

    async def create_take_profit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        take_profit_price: float,
    ) -> dict[str, Any]:
        return await self._instrumented_async(
            "create_take_profit_order",
            lambda: self._wrapped.create_take_profit_order(
                symbol, side, quantity, take_profit_price
            ),
        )

    async def create_trailing_stop_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        activation_price: float,
        callback_rate: float,
    ) -> dict[str, Any]:
        return await self._instrumented_async(
            "create_trailing_stop_order",
            lambda: self._wrapped.create_trailing_stop_order(
                symbol, side, quantity, activation_price, callback_rate
            ),
        )

    async def cancel_all_orders(self, symbol: str) -> None:
        return await self._instrumented_async(
            "cancel_all_orders",
            lambda: self._wrapped.cancel_all_orders(symbol),
        )

    async def fetch_open_orders(self, symbol: str) -> list[dict[str, Any]]:
        return await self._instrumented_async(
            "fetch_open_orders",
            lambda: self._wrapped.fetch_open_orders(symbol),
        )

    async def fetch_order(self, order_id: str, symbol: str) -> dict:
        return await self._instrumented_async(
            "fetch_order",
            lambda: self._wrapped.fetch_order(order_id, symbol),
        )

    # ─── Sync métodos (não instrumentados) ─────────────────────────────────────

    def get_quantity_precision(self, symbol: str) -> int:
        """Método sync em memória — não há chamada API."""
        return self._wrapped.get_quantity_precision(symbol)

    def round_quantity(self, symbol: str, qty: float) -> float:
        """Método sync em memória — não há chamada API."""
        return self._wrapped.round_quantity(symbol, qty)

    def round_price(self, symbol: str, price: float) -> float:
        """Método sync em memória — não há chamada API."""
        return self._wrapped.round_price(symbol, price)

    # ─── Helpers internos ───────────────────────────────────────────────────────

    async def _instrumented_async(
        self,
        endpoint: str,
        coro_fn: Callable[[], Any],
    ) -> Any:
        """
        Helper DRY para instrumentar coroutines async.

        Mede tempo, incrementa api_requests_total (success/error), e
        errors_total em caso de exceção. Propaga a exceção para o caller.
        """
        try:
            result = await coro_fn()
            record_api_request(endpoint, "success")
            return result
        except Exception as exc:
            record_api_request(endpoint, "error")
            record_error("exchange", type(exc).__name__)
            raise
