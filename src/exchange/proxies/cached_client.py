"""Proxy de cache para BinanceClient.

Reduz chamadas redundantes à exchange cacheando metadados de mercado
com TTL configurável.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from src.monitoring.logger import get_logger

logger = get_logger(__name__)

DEFAULT_CACHE_TTL_SECONDS: int = 3600  # 1 hora


class _CacheEntry:
    """Entrada de cache com timestamp de expiração."""

    def __init__(self, value: Any, ttl_seconds: int) -> None:
        self.value = value
        self.expires_at = time.monotonic() + ttl_seconds

    def is_expired(self) -> bool:
        return time.monotonic() > self.expires_at


class CachedBinanceClient:
    """Proxy que envolve BinanceClient com cache de metadados.

    Cacheia métodos síncronos que consultam mercados já carregados:
    - get_quantity_precision(symbol)
    - get_price_precision(symbol)  (via round_price)
    - get_market_info(symbol)      (via markets dict)

    O cache é thread-safe via asyncio.Lock.
    """

    def __init__(
        self,
        client: Any,
        ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
    ) -> None:
        self._client = client
        self._ttl = ttl_seconds
        self._cache: dict[str, _CacheEntry] = {}
        self._lock = asyncio.Lock()

    # ─── Proxy transparente ───────────────────────────────────────────────────

    def __getattr__(self, name: str) -> Any:
        """Delega atributos não-cacheados para o cliente real."""
        return getattr(self._client, name)

    # ─── Métodos cacheados ──────────────────────────────────────────────────

    async def get_quantity_precision(self, symbol: str) -> int:
        """Retorna casas decimais para quantidade, com cache."""
        return await self._get_cached(
            key=f"qty_precision:{symbol}",
            fetcher=lambda: self._client.get_quantity_precision(symbol),
        )

    async def get_price_precision(self, symbol: str) -> int:
        """Retorna casas decimais para preço, com cache."""
        return await self._get_cached(
            key=f"price_precision:{symbol}",
            fetcher=lambda: self._client.get_price_precision(symbol),
        )

    async def get_market_info(self, symbol: str) -> dict[str, Any]:
        """Retorna informações do mercado, com cache."""
        return await self._get_cached(
            key=f"market_info:{symbol}",
            fetcher=lambda: self._client.get_market_info(symbol),
        )

    # ─── Cache interno ──────────────────────────────────────────────────────

    async def _get_cached(self, key: str, fetcher: Any) -> Any:
        """Busca do cache ou executa fetcher e armazena."""
        async with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired():
                logger.debug("cache_hit", key=key)
                return entry.value

        # Fora do lock para não bloquear outras threads durante fetch
        value = fetcher()

        async with self._lock:
            self._cache[key] = _CacheEntry(value, self._ttl)
            logger.debug("cache_miss", key=key, ttl=self._ttl)

        return value

    async def invalidate_cache(self, pattern: str | None = None) -> None:
        """Invalida entradas do cache. pattern=None → limpa tudo."""
        async with self._lock:
            if pattern is None:
                count = len(self._cache)
                self._cache.clear()
                logger.info("cache_cleared_all", count=count)
            else:
                keys_to_remove = [k for k in self._cache if pattern in k]
                for k in keys_to_remove:
                    del self._cache[k]
                logger.info("cache_invalidated", pattern=pattern, count=len(keys_to_remove))

    def get_cache_stats(self) -> dict[str, Any]:
        """Retorna estatísticas do cache para monitoramento."""
        total = len(self._cache)
        expired = sum(1 for e in self._cache.values() if e.is_expired())
        return {
            "total_entries": total,
            "expired_entries": expired,
            "valid_entries": total - expired,
            "ttl_seconds": self._ttl,
        }
