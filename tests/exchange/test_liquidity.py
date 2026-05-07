"""
Testes de conformidade SPEC_018 — validação de liquidez em startup.

Cobre:
- Par com volume e OI suficientes: sem erro
- Par com volume_24h insuficiente: InsufficientLiquidityError
- Par com open_interest insuficiente: InsufficientLiquidityError
- Falha ao buscar OI (exchange indisponível): trata como OI=0
- fetch_quantity_precision_map: retorna precisão por símbolo
- fetch_quantity_precision_map: símbolo não encontrado ignorado
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.exchange.binance_client import BinanceClient, InsufficientLiquidityError


def _make_client() -> BinanceClient:
    with patch("src.exchange.binance_client.ccxt"):
        settings = MagicMock()
        settings.binance_api_key = "key"
        settings.binance_api_secret = "secret"
        settings.binance_testnet = False
        client = BinanceClient.__new__(BinanceClient)
        client._settings = settings
        client._exchange = MagicMock()
        return client


@pytest.mark.asyncio
async def test_validate_liquidity_ok() -> None:
    client = _make_client()
    client._exchange.fetch_ticker = AsyncMock(return_value={"quoteVolume": 600_000})
    client._exchange.fetch_open_interest = AsyncMock(
        return_value={"openInterestValue": 300_000}
    )

    await client.validate_market_liquidity("XPTUSDT")


@pytest.mark.asyncio
async def test_validate_liquidity_volume_insuficiente() -> None:
    client = _make_client()
    client._exchange.fetch_ticker = AsyncMock(return_value={"quoteVolume": 400_000})
    client._exchange.fetch_open_interest = AsyncMock(
        return_value={"openInterestValue": 300_000}
    )

    with pytest.raises(InsufficientLiquidityError, match="volume_24h"):
        await client.validate_market_liquidity("COPPERUSDT")


@pytest.mark.asyncio
async def test_validate_liquidity_oi_insuficiente() -> None:
    client = _make_client()
    client._exchange.fetch_ticker = AsyncMock(return_value={"quoteVolume": 700_000})
    client._exchange.fetch_open_interest = AsyncMock(
        return_value={"openInterestValue": 100_000}
    )

    with pytest.raises(InsufficientLiquidityError, match="open_interest"):
        await client.validate_market_liquidity("XPTUSDT")


@pytest.mark.asyncio
async def test_validate_liquidity_oi_fetch_falha_trata_como_zero() -> None:
    client = _make_client()
    client._exchange.fetch_ticker = AsyncMock(return_value={"quoteVolume": 700_000})
    client._exchange.fetch_open_interest = AsyncMock(
        side_effect=RuntimeError("indisponível")
    )

    with pytest.raises(InsufficientLiquidityError, match="open_interest"):
        await client.validate_market_liquidity("XPTUSDT")


@pytest.mark.asyncio
async def test_fetch_quantity_precision_map() -> None:
    client = _make_client()
    client._exchange.load_markets = AsyncMock(
        return_value={
            "XPTUSDT": {"precision": {"amount": 2}},
            "BTCUSDT": {"precision": {"amount": 3}},
        }
    )

    result = await client.fetch_quantity_precision_map(["XPTUSDT", "BTCUSDT"])

    assert result == {"XPTUSDT": 2, "BTCUSDT": 3}


@pytest.mark.asyncio
async def test_fetch_quantity_precision_map_simbolo_ausente() -> None:
    client = _make_client()
    client._exchange.load_markets = AsyncMock(
        return_value={"BTCUSDT": {"precision": {"amount": 3}}}
    )

    result = await client.fetch_quantity_precision_map(["XPTUSDT", "BTCUSDT"])

    assert "XPTUSDT" not in result
    assert result["BTCUSDT"] == 3
