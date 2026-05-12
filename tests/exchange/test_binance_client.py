"""Testes de priceProtect nas ordens do BinanceClient (SPEC_043)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import ccxt.async_support as ccxt
import pytest

from src.exchange.binance_client import BinanceClient


def _make_client() -> BinanceClient:
    """Cria BinanceClient com settings mockadas."""
    settings = MagicMock()
    settings.binance_api_key = "test_key"
    settings.binance_api_secret = "test_secret"
    settings.binance_testnet = True
    with patch("ccxt.async_support.binanceusdm"):
        return BinanceClient(settings)


def _mock_exchange_create_order(
    client: BinanceClient,
    side_effect=None,
    return_value=None,
) -> AsyncMock:
    """Substitui _exchange.create_order por AsyncMock e retorna o mock."""
    mock = AsyncMock(side_effect=side_effect, return_value=return_value)
    client._exchange.create_order = mock  # type: ignore[method-assign]
    return mock


class TestPriceProtectStopLoss:
    """TEST-043-01: priceProtect em STOP_MARKET."""

    @pytest.mark.asyncio
    async def test_stop_loss_has_price_protect(self) -> None:
        """create_stop_loss_order envia priceProtect=True nos params."""
        client = _make_client()
        mock_create = _mock_exchange_create_order(client, return_value={"id": "123", "status": "new"})

        await client.create_stop_loss_order("BTCUSDT", "sell", 0.01, 60000.0)

        assert mock_create.called
        _, kwargs = mock_create.call_args
        assert kwargs.get("type") == "STOP_MARKET"
        params = kwargs.get("params", {})
        assert params.get("priceProtect") is True

    @pytest.mark.asyncio
    async def test_stop_loss_bad_request_fallback(self) -> None:
        """Se ccxt.BadRequest no STOP_MARKET, fallback sem priceProtect."""
        client = _make_client()
        bad_req = ccxt.BadRequest("priceProtect not supported")
        ok_response = {"id": "456", "status": "new"}
        mock_create = _mock_exchange_create_order(
            client,
            side_effect=[bad_req, ok_response],
        )

        result = await client.create_stop_loss_order("ETHUSDT", "sell", 0.1, 3000.0)

        assert mock_create.call_count == 2
        # Primeira chamada: com priceProtect
        params1 = mock_create.call_args_list[0].kwargs.get("params", {})
        assert params1.get("priceProtect") is True
        # Segunda chamada: sem priceProtect
        params2 = mock_create.call_args_list[1].kwargs.get("params", {})
        assert "priceProtect" not in params2 or params2.get("priceProtect") is None
        assert result["id"] == "456"

    @pytest.mark.asyncio
    async def test_stop_loss_non_bad_request_propaga(self) -> None:
        """Exceção não-BadRequest no STOP_MARKET propaga sem fallback."""
        client = _make_client()
        mock_create = _mock_exchange_create_order(
            client,
            side_effect=ccxt.AuthenticationError("invalid key"),
        )

        with pytest.raises(ccxt.AuthenticationError):
            await client.create_stop_loss_order("BTCUSDT", "sell", 0.01, 60000.0)

        assert mock_create.call_count == 1


class TestPriceProtectTakeProfit:
    """TEST-043-02: priceProtect em TAKE_PROFIT_MARKET."""

    @pytest.mark.asyncio
    async def test_take_profit_has_price_protect(self) -> None:
        """create_take_profit_order envia priceProtect=True nos params."""
        client = _make_client()
        mock_create = _mock_exchange_create_order(client, return_value={"id": "789", "status": "new"})

        await client.create_take_profit_order("BTCUSDT", "sell", 0.01, 65000.0)

        assert mock_create.called
        _, kwargs = mock_create.call_args
        assert kwargs.get("type") == "TAKE_PROFIT_MARKET"
        params = kwargs.get("params", {})
        assert params.get("priceProtect") is True

    @pytest.mark.asyncio
    async def test_take_profit_bad_request_fallback(self) -> None:
        """Se ccxt.BadRequest no TAKE_PROFIT_MARKET, fallback sem priceProtect."""
        client = _make_client()
        bad_req = ccxt.BadRequest("priceProtect not supported")
        ok_response = {"id": "101", "status": "new"}
        mock_create = _mock_exchange_create_order(
            client,
            side_effect=[bad_req, ok_response],
        )

        result = await client.create_take_profit_order("ETHUSDT", "sell", 0.1, 3200.0)

        assert mock_create.call_count == 2
        params1 = mock_create.call_args_list[0].kwargs.get("params", {})
        assert params1.get("priceProtect") is True
        params2 = mock_create.call_args_list[1].kwargs.get("params", {})
        assert "priceProtect" not in params2 or params2.get("priceProtect") is None
        assert result["id"] == "101"

    @pytest.mark.asyncio
    async def test_take_profit_non_bad_request_propaga(self) -> None:
        """Exceção não-BadRequest no TAKE_PROFIT_MARKET propaga sem fallback."""
        client = _make_client()
        mock_create = _mock_exchange_create_order(
            client,
            side_effect=ccxt.InsufficientFunds("no balance"),
        )

        with pytest.raises(ccxt.InsufficientFunds):
            await client.create_take_profit_order("BTCUSDT", "sell", 0.01, 65000.0)

        assert mock_create.call_count == 1


class TestPriceProtectTrailingStop:
    """TEST-043-17: priceProtect em TRAILING_STOP_MARKET."""

    @pytest.mark.asyncio
    async def test_trailing_stop_tenta_price_protect(self) -> None:
        """create_trailing_stop_order tenta priceProtect=True."""
        client = _make_client()
        mock_create = _mock_exchange_create_order(
            client,
            return_value={"id": "999", "status": "new"},
        )

        await client.create_trailing_stop_order(
            "BTCUSDT", "sell", 0.01,
            activation_price=62000.0,
            callback_rate=0.5,
        )

        assert mock_create.called
        _, kwargs = mock_create.call_args
        params = kwargs.get("params", {})
        assert params.get("priceProtect") is True
        assert params.get("trailingPercent") == 0.5

    @pytest.mark.asyncio
    async def test_trailing_stop_bad_request_fallback(self) -> None:
        """TEST-043-17: Trailing + BadRequest → fallback sem priceProtect + WARN."""
        client = _make_client()
        bad_req = ccxt.BadRequest("not supported")
        ok_response = {"id": "111", "status": "new"}
        mock_create = _mock_exchange_create_order(
            client,
            side_effect=[bad_req, ok_response],
        )

        result = await client.create_trailing_stop_order(
            "ETHUSDT", "sell", 0.1,
            activation_price=3100.0,
            callback_rate=0.5,
        )

        assert mock_create.call_count == 2
        params1 = mock_create.call_args_list[0].kwargs.get("params", {})
        assert params1.get("priceProtect") is True
        params2 = mock_create.call_args_list[1].kwargs.get("params", {})
        assert "priceProtect" not in params2 or params2.get("priceProtect") is None
        assert result["id"] == "111"

    @pytest.mark.asyncio
    async def test_trailing_stop_auth_error_propaga(self) -> None:
        """TEST-043-17b: Trailing + AuthenticationError → propaga exceção, sem fallback."""
        client = _make_client()
        mock_create = _mock_exchange_create_order(
            client,
            side_effect=ccxt.AuthenticationError("bad credentials"),
        )

        with pytest.raises(ccxt.AuthenticationError):
            await client.create_trailing_stop_order(
                "BTCUSDT", "sell", 0.01,
                activation_price=62000.0,
                callback_rate=0.5,
            )

        assert mock_create.call_count == 1

    @pytest.mark.asyncio
    async def test_trailing_stop_insufficient_funds_propaga(self) -> None:
        """Exceção não-BadRequest no trailing stop propaga sem fallback."""
        client = _make_client()
        mock_create = _mock_exchange_create_order(
            client,
            side_effect=ccxt.InsufficientFunds("no balance"),
        )

        with pytest.raises(ccxt.InsufficientFunds):
            await client.create_trailing_stop_order(
                "BTCUSDT", "sell", 0.01,
                activation_price=62000.0,
                callback_rate=0.5,
            )

        assert mock_create.call_count == 1
