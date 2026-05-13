"""Testes para CachedBinanceClient."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from src.exchange.proxies.cached_client import CachedBinanceClient


class FakeClient:
    """Cliente fake para testes de cache."""

    def __init__(self) -> None:
        self.call_count = 0

    def get_quantity_precision(self, symbol: str) -> int:
        self.call_count += 1
        return 3

    def get_price_precision(self, symbol: str) -> int:
        self.call_count += 1
        return 2

    def get_market_info(self, symbol: str) -> dict[str, Any]:
        self.call_count += 1
        return {"symbol": symbol, "type": "future"}


@pytest.fixture
def fake_client() -> FakeClient:
    return FakeClient()


@pytest.fixture
def cached_client(fake_client: FakeClient) -> CachedBinanceClient:
    return CachedBinanceClient(client=fake_client, ttl_seconds=3600)


# ─── Cache Hit / Miss ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cache_miss_on_first_call(
    cached_client: CachedBinanceClient, fake_client: FakeClient
) -> None:
    """Primeira chamada deve executar o fetcher."""
    result = await cached_client.get_quantity_precision("BTCUSDT")
    assert result == 3
    assert fake_client.call_count == 1


@pytest.mark.asyncio
async def test_cache_hit_on_second_call(
    cached_client: CachedBinanceClient, fake_client: FakeClient
) -> None:
    """Segunda chamada deve usar cache."""
    await cached_client.get_quantity_precision("BTCUSDT")
    fake_client.call_count = 0  # Reset

    result = await cached_client.get_quantity_precision("BTCUSDT")
    assert result == 3
    assert fake_client.call_count == 0  # Não chamou o cliente real


@pytest.mark.asyncio
async def test_cache_different_keys(
    cached_client: CachedBinanceClient, fake_client: FakeClient
) -> None:
    """Chaves diferentes devem ter caches separados."""
    await cached_client.get_quantity_precision("BTCUSDT")
    await cached_client.get_quantity_precision("ETHUSDT")
    assert fake_client.call_count == 2


# ─── TTL Expiration ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cache_expiration(fake_client: FakeClient) -> None:
    """Cache deve expirar após TTL."""
    import asyncio

    client = CachedBinanceClient(
        client=fake_client, ttl_seconds=0
    )  # TTL zero = expira imediatamente
    await client.get_quantity_precision("BTCUSDT")
    await asyncio.sleep(0.01)  # Dá tempo para expirar
    fake_client.call_count = 0

    result = await client.get_quantity_precision("BTCUSDT")
    assert result == 3
    assert fake_client.call_count == 1  # Re-executou porque expirou


# ─── Métodos Cacheados ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_price_precision_cached(
    cached_client: CachedBinanceClient, fake_client: FakeClient
) -> None:
    """get_price_precision deve ser cacheado."""
    await cached_client.get_price_precision("BTCUSDT")
    fake_client.call_count = 0
    result = await cached_client.get_price_precision("BTCUSDT")
    assert result == 2
    assert fake_client.call_count == 0


@pytest.mark.asyncio
async def test_get_market_info_cached(
    cached_client: CachedBinanceClient, fake_client: FakeClient
) -> None:
    """get_market_info deve ser cacheado."""
    await cached_client.get_market_info("BTCUSDT")
    fake_client.call_count = 0
    result = await cached_client.get_market_info("BTCUSDT")
    assert result == {"symbol": "BTCUSDT", "type": "future"}
    assert fake_client.call_count == 0


# ─── Invalidação ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invalidate_all_cache(
    cached_client: CachedBinanceClient, fake_client: FakeClient
) -> None:
    """invalidate_cache sem pattern deve limpar tudo."""
    await cached_client.get_quantity_precision("BTCUSDT")
    await cached_client.get_price_precision("BTCUSDT")

    await cached_client.invalidate_cache()
    fake_client.call_count = 0

    await cached_client.get_quantity_precision("BTCUSDT")
    assert fake_client.call_count == 1  # Re-executou


@pytest.mark.asyncio
async def test_invalidate_by_pattern(
    cached_client: CachedBinanceClient, fake_client: FakeClient
) -> None:
    """invalidate_cache com pattern deve remover apenas matching."""
    await cached_client.get_quantity_precision("BTCUSDT")
    await cached_client.get_price_precision("BTCUSDT")

    await cached_client.invalidate_cache("qty_precision")
    fake_client.call_count = 0

    await cached_client.get_quantity_precision("BTCUSDT")
    assert fake_client.call_count == 1  # Re-executou

    await cached_client.get_price_precision("BTCUSDT")
    assert fake_client.call_count == 1  # Não re-executou (ainda em cache)


# ─── Thread Safety ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_concurrent_access(fake_client: FakeClient) -> None:
    """Múltiplas chamadas concorrentes devem ser thread-safe."""
    client = CachedBinanceClient(client=fake_client, ttl_seconds=3600)

    async def fetch() -> int:
        return await client.get_quantity_precision("BTCUSDT")

    results = await asyncio.gather(*[fetch() for _ in range(10)])
    assert all(r == 3 for r in results)
    # Deve ter chamado apenas uma vez (primeira miss, resto hit)
    assert fake_client.call_count == 1


# ─── Estatísticas ───────────────────────────────────────────────────────────


def test_cache_stats(cached_client: CachedBinanceClient) -> None:
    """get_cache_stats deve retornar estatísticas corretas."""
    stats = cached_client.get_cache_stats()
    assert stats["total_entries"] == 0
    assert stats["expired_entries"] == 0
    assert stats["valid_entries"] == 0
    assert stats["ttl_seconds"] == 3600


# ─── Proxy Transparente ───────────────────────────────────────────────────


def test_proxy_transparent_delegation(fake_client: FakeClient) -> None:
    """Atributos não-cacheados devem ser delegados."""
    client = CachedBinanceClient(client=fake_client)
    assert client.call_count == 0  # Delegado para fake_client
