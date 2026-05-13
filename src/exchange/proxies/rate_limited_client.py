"""Proxy de rate limiting para BinanceClient.

Controla concorrência de chamadas à exchange via semaphore,
evitando rate limits e sobrecarga.
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.monitoring.logger import get_logger

logger = get_logger(__name__)

DEFAULT_MAX_CONCURRENT: int = 5


class RateLimitedBinanceClient:
    """Proxy que envolve BinanceClient com controle de concorrência.

    Usa asyncio.Semaphore para limitar chamadas simultâneas à exchange.
    Configurável via Settings (max_concurrent_requests).
    """

    def __init__(
        self,
        client: Any,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    ) -> None:
        self._client = client
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_concurrent = max_concurrent
        self._stats = {
            "total_requests": 0,
            "queued_requests": 0,
            "active_requests": 0,
        }
        self._stats_lock = asyncio.Lock()

    # ─── Proxy transparente ─────────────────────────────────────────────────

    def __getattr__(self, name: str) -> Any:
        """Delega atributos não-controlados para o cliente real."""
        return getattr(self._client, name)

    # ─── Métodos rate-limited ───────────────────────────────────────────────

    async def fetch_ohlcv(self, *args: Any, **kwargs: Any) -> Any:
        """Fetch OHLCV com rate limiting."""
        return await self._execute_with_limit(
            self._client.fetch_ohlcv, *args, **kwargs
        )

    async def fetch_balance(self, *args: Any, **kwargs: Any) -> Any:
        """Fetch balance com rate limiting."""
        return await self._execute_with_limit(
            self._client.fetch_balance, *args, **kwargs
        )

    async def fetch_open_positions(self, *args: Any, **kwargs: Any) -> Any:
        """Fetch positions com rate limiting."""
        return await self._execute_with_limit(
            self._client.fetch_open_positions, *args, **kwargs
        )

    async def create_market_order(self, *args: Any, **kwargs: Any) -> Any:
        """Create market order com rate limiting."""
        return await self._execute_with_limit(
            self._client.create_market_order, *args, **kwargs
        )

    async def create_stop_loss_order(self, *args: Any, **kwargs: Any) -> Any:
        """Create stop loss com rate limiting."""
        return await self._execute_with_limit(
            self._client.create_stop_loss_order, *args, **kwargs
        )

    async def create_take_profit_order(self, *args: Any, **kwargs: Any) -> Any:
        """Create take profit com rate limiting."""
        return await self._execute_with_limit(
            self._client.create_take_profit_order, *args, **kwargs
        )

    async def cancel_all_orders(self, *args: Any, **kwargs: Any) -> Any:
        """Cancel orders com rate limiting."""
        return await self._execute_with_limit(
            self._client.cancel_all_orders, *args, **kwargs
        )

    async def fetch_open_orders(self, *args: Any, **kwargs: Any) -> Any:
        """Fetch open orders com rate limiting."""
        return await self._execute_with_limit(
            self._client.fetch_open_orders, *args, **kwargs
        )

    async def fetch_order(self, *args: Any, **kwargs: Any) -> Any:
        """Fetch order com rate limiting."""
        return await self._execute_with_limit(
            self._client.fetch_order, *args, **kwargs
        )

    async def fetch_ticker(self, *args: Any, **kwargs: Any) -> Any:
        """Fetch ticker com rate limiting."""
        return await self._execute_with_limit(
            self._client.fetch_ticker, *args, **kwargs
        )

    async def set_leverage(self, *args: Any, **kwargs: Any) -> Any:
        """Set leverage com rate limiting."""
        return await self._execute_with_limit(
            self._client.set_leverage, *args, **kwargs
        )

    async def set_margin_mode(self, *args: Any, **kwargs: Any) -> Any:
        """Set margin mode com rate limiting."""
        return await self._execute_with_limit(
            self._client.set_margin_mode, *args, **kwargs
        )

    # ─── Execução com semaphore ─────────────────────────────────────────────

    async def _execute_with_limit(self, method: Any, *args: Any, **kwargs: Any) -> Any:
        """Executa método respeitando o semaphore."""
        async with self._stats_lock:
            self._stats["total_requests"] += 1
            self._stats["queued_requests"] += 1

        logger.debug(
            "rate_limit_queued",
            method=method.__name__,
            queue_size=self._stats["queued_requests"],
            max_concurrent=self._max_concurrent,
        )

        async with self._semaphore:
            async with self._stats_lock:
                self._stats["queued_requests"] -= 1
                self._stats["active_requests"] += 1

            try:
                logger.debug(
                    "rate_limit_executing",
                    method=method.__name__,
                    active=self._stats["active_requests"],
                )
                return await method(*args, **kwargs)
            finally:
                async with self._stats_lock:
                    self._stats["active_requests"] -= 1

    def get_rate_limit_stats(self) -> dict[str, Any]:
        """Retorna estatísticas de rate limiting."""
        return {
            "max_concurrent": self._max_concurrent,
            "total_requests": self._stats["total_requests"],
            "queued_requests": self._stats["queued_requests"],
            "active_requests": self._stats["active_requests"],
        }
