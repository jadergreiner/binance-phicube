"""Testes para RateLimitedBinanceClient."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from src.exchange.proxies.rate_limited_client import RateLimitedBinanceClient


class FakeAsyncClient:
    """Cliente async fake para testes de rate limiting."""

    def __init__(self) -> None:
        self.active_calls = 0
        self.max_concurrent = 0
        self.call_count = 0

    async def fetch_ohlcv(self, symbol: str, timeframe: str) -> str:
        self.call_count += 1
        self.active_calls += 1
        self.max_concurrent = max(self.max_concurrent, self.active_calls)
        await asyncio.sleep(0.01)  # Simula latência
        self.active_calls -= 1
        return f"{symbol}_{timeframe}"

    async def fetch_balance(self) -> dict[str, Any]:
        self.call_count += 1
        self.active_calls += 1
        self.max_concurrent = max(self.max_concurrent, self.active_calls)
        await asyncio.sleep(0.01)
        self.active_calls -= 1
        return {"USDT": {"free": 1000.0}}

    async def create_market_order(self, symbol: str, side: str, quantity: float) -> dict[str, Any]:
        self.call_count += 1
        self.active_calls += 1
        self.max_concurrent = max(self.max_concurrent, self.active_calls)
        await asyncio.sleep(0.01)
        self.active_calls -= 1
        return {"id": "123", "symbol": symbol}

    async def fetch_open_positions(self) -> list[dict[str, Any]]:
        self.call_count += 1
        self.active_calls += 1
        self.max_concurrent = max(self.max_concurrent, self.active_calls)
        await asyncio.sleep(0.01)
        self.active_calls -= 1
        return [{"symbol": "BTCUSDT"}]

    async def create_stop_loss_order(
        self, symbol: str, side: str, quantity: float, stop_price: float
    ) -> dict[str, Any]:
        self.call_count += 1
        self.active_calls += 1
        self.max_concurrent = max(self.max_concurrent, self.active_calls)
        await asyncio.sleep(0.01)
        self.active_calls -= 1
        return {"id": "sl-123", "symbol": symbol}

    async def create_take_profit_order(
        self, symbol: str, side: str, quantity: float, take_profit_price: float
    ) -> dict[str, Any]:
        self.call_count += 1
        self.active_calls += 1
        self.max_concurrent = max(self.max_concurrent, self.active_calls)
        await asyncio.sleep(0.01)
        self.active_calls -= 1
        return {"id": "tp-123", "symbol": symbol}

    async def cancel_all_orders(self, symbol: str) -> None:
        self.call_count += 1
        self.active_calls += 1
        self.max_concurrent = max(self.max_concurrent, self.active_calls)
        await asyncio.sleep(0.01)
        self.active_calls -= 1

    async def fetch_open_orders(self, symbol: str) -> list[dict[str, Any]]:
        self.call_count += 1
        self.active_calls += 1
        self.max_concurrent = max(self.max_concurrent, self.active_calls)
        await asyncio.sleep(0.01)
        self.active_calls -= 1
        return []

    async def fetch_order(self, order_id: str, symbol: str) -> dict[str, Any]:
        self.call_count += 1
        self.active_calls += 1
        self.max_concurrent = max(self.max_concurrent, self.active_calls)
        await asyncio.sleep(0.01)
        self.active_calls -= 1
        return {"id": order_id, "symbol": symbol}

    async def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        self.call_count += 1
        self.active_calls += 1
        self.max_concurrent = max(self.max_concurrent, self.active_calls)
        await asyncio.sleep(0.01)
        self.active_calls -= 1
        return {"symbol": symbol, "last": 50000.0}

    async def set_leverage(self, symbol: str, leverage: int) -> None:
        self.call_count += 1
        self.active_calls += 1
        self.max_concurrent = max(self.max_concurrent, self.active_calls)
        await asyncio.sleep(0.01)
        self.active_calls -= 1

    async def set_margin_mode(self, symbol: str, mode: str) -> None:
        self.call_count += 1
        self.active_calls += 1
        self.max_concurrent = max(self.max_concurrent, self.active_calls)
        await asyncio.sleep(0.01)
        self.active_calls -= 1


@pytest.fixture
def fake_client() -> FakeAsyncClient:
    return FakeAsyncClient()


@pytest.fixture
def rate_limited_client(fake_client: FakeAsyncClient) -> RateLimitedBinanceClient:
    return RateLimitedBinanceClient(client=fake_client, max_concurrent=2)


# ─── Rate Limiting Básico ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rate_limit_enforced(
    rate_limited_client: RateLimitedBinanceClient, fake_client: FakeAsyncClient
) -> None:
    """Deve respeitar o limite de concorrência."""
    tasks = [rate_limited_client.fetch_ohlcv("BTCUSDT", "15m") for _ in range(5)]
    results = await asyncio.gather(*tasks)
    assert all(r == "BTCUSDT_15m" for r in results)
    assert fake_client.max_concurrent <= 2


@pytest.mark.asyncio
async def test_rate_limit_different_methods(
    rate_limited_client: RateLimitedBinanceClient, fake_client: FakeAsyncClient
) -> None:
    """Limite deve ser global entre métodos diferentes."""
    tasks = [
        rate_limited_client.fetch_ohlcv("BTCUSDT", "15m"),
        rate_limited_client.fetch_balance(),
        rate_limited_client.create_market_order("BTCUSDT", "buy", 0.1),
        rate_limited_client.fetch_ohlcv("ETHUSDT", "1h"),
    ]
    await asyncio.gather(*tasks)
    assert fake_client.max_concurrent <= 2


# ─── Estatísticas ───────────────────────────────────────────────────────────


def test_rate_limit_stats(rate_limited_client: RateLimitedBinanceClient) -> None:
    """get_rate_limit_stats deve retornar estatísticas iniciais."""
    stats = rate_limited_client.get_rate_limit_stats()
    assert stats["max_concurrent"] == 2
    assert stats["total_requests"] == 0
    assert stats["queued_requests"] == 0
    assert stats["active_requests"] == 0


@pytest.mark.asyncio
async def test_rate_limit_stats_after_calls(rate_limited_client: RateLimitedBinanceClient) -> None:
    """Estatísticas devem refletir chamadas."""
    await rate_limited_client.fetch_ohlcv("BTCUSDT", "15m")
    stats = rate_limited_client.get_rate_limit_stats()
    assert stats["total_requests"] == 1


# ─── Proxy Transparente ───────────────────────────────────────────────────


def test_proxy_transparent_delegation(fake_client: FakeAsyncClient) -> None:
    """Atributos não-controlados devem ser delegados."""
    client = RateLimitedBinanceClient(client=fake_client)
    assert client.call_count == 0  # Delegado para fake_client


# ─── Configuração ───────────────────────────────────────────────────────────


def test_custom_max_concurrent(fake_client: FakeAsyncClient) -> None:
    """Deve aceitar configuração customizada de max_concurrent."""
    client = RateLimitedBinanceClient(client=fake_client, max_concurrent=10)
    assert client.get_rate_limit_stats()["max_concurrent"] == 10


# ─── Métodos Rate-Limited ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_balance_rate_limited(rate_limited_client: RateLimitedBinanceClient) -> None:
    """fetch_balance deve ser rate-limited."""
    result = await rate_limited_client.fetch_balance()
    assert result == {"USDT": {"free": 1000.0}}


@pytest.mark.asyncio
async def test_create_market_order_rate_limited(
    rate_limited_client: RateLimitedBinanceClient,
) -> None:
    """create_market_order deve ser rate-limited."""
    result = await rate_limited_client.create_market_order("BTCUSDT", "buy", 0.1)
    assert result["id"] == "123"


@pytest.mark.asyncio
async def test_all_methods_rate_limited(fake_client: FakeAsyncClient) -> None:
    """Todos os métodos async devem ser rate-limited."""
    client = RateLimitedBinanceClient(client=fake_client, max_concurrent=1)

    # Testa todos os métodos rate-limited
    await client.fetch_ohlcv("BTCUSDT", "15m")
    await client.fetch_balance()
    await client.fetch_open_positions()
    await client.create_market_order("BTCUSDT", "buy", 0.1)
    await client.create_stop_loss_order("BTCUSDT", "sell", 0.1, 50000.0)
    await client.create_take_profit_order("BTCUSDT", "sell", 0.1, 60000.0)
    await client.cancel_all_orders("BTCUSDT")
    await client.fetch_open_orders("BTCUSDT")
    await client.fetch_order("123", "BTCUSDT")
    await client.fetch_ticker("BTCUSDT")
    await client.set_leverage("BTCUSDT", 5)
    await client.set_margin_mode("BTCUSDT", "isolated")

    assert fake_client.call_count == 12
