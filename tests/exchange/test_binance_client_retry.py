"""Testes de retry do BinanceClient (SPEC_007 task_001)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import ccxt.async_support as ccxt
import pytest

from src.exchange.binance_client import BinanceClient


def _make_client() -> BinanceClient:
    settings = MagicMock()
    settings.binance_api_key = "test_key"
    settings.binance_api_secret = "test_secret"
    settings.binance_testnet = True
    with patch("ccxt.async_support.binanceusdm"):
        return BinanceClient(settings)


class TestFetchOhlcvWithRetry:
    """TEST_007_01 a TEST_007_04 — retry com backoff exponencial."""

    @pytest.mark.asyncio
    async def test_retry_em_network_error_com_backoff(self) -> None:
        """TEST_007_01: 2 falhas NetworkError + 1 sucesso — backoff exponencial."""
        import pandas as pd

        client = _make_client()
        df_ok = pd.DataFrame(
            {"open_time": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
        )

        call_count = 0

        async def fake_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ccxt.NetworkError("timeout")
            return df_ok

        sleep_delays: list[float] = []

        async def fake_sleep(delay: float) -> None:
            sleep_delays.append(delay)

        client.fetch_ohlcv = fake_fetch

        with patch("src.exchange.binance_client.asyncio.sleep", side_effect=fake_sleep):
            await client.fetch_ohlcv_with_retry("BTCUSDT", "4h", retries=3, base_delay=1.0)

        assert call_count == 3
        assert len(sleep_delays) == 2
        assert sleep_delays[0] == 1.0
        assert sleep_delays[1] == 2.0

    @pytest.mark.asyncio
    async def test_erro_fatal_nao_entra_em_retry(self) -> None:
        """TEST_007_02: AuthenticationError → falha imediata, sem retry."""
        client = _make_client()
        call_count = 0

        async def fake_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise ccxt.AuthenticationError("invalid key")

        client.fetch_ohlcv = fake_fetch

        with pytest.raises(ccxt.AuthenticationError):
            await client.fetch_ohlcv_with_retry("BTCUSDT", "4h", retries=3)

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_esgotado_relanca_runtime_error(self) -> None:
        """TEST_007_03: 3 falhas NetworkError → RuntimeError com causa original."""
        client = _make_client()

        async def fake_fetch(*args, **kwargs):
            raise ccxt.NetworkError("connection reset")

        async def fake_sleep(_: float) -> None:
            pass

        client.fetch_ohlcv = fake_fetch

        with patch("src.exchange.binance_client.asyncio.sleep", side_effect=fake_sleep):
            with pytest.raises(RuntimeError) as exc_info:
                await client.fetch_ohlcv_with_retry("BTCUSDT", "4h", retries=3)

        assert "after 3 retries" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, ccxt.NetworkError)

    @pytest.mark.asyncio
    async def test_log_retry_nao_contem_str_exc(self, capfd) -> None:
        """TEST_007_04: log de retry usa error_type, nunca str(exc) com URL/token.

        structlog escreve em stdout/stderr nos testes — capfd captura o output real.
        """
        client = _make_client()
        fake_url = "https://fake_token_here:secret@testnet.binancefuture.com/fapi"

        async def fake_fetch(*args, **kwargs):
            raise ccxt.NetworkError(fake_url)

        async def fake_sleep(_: float) -> None:
            pass

        client.fetch_ohlcv = fake_fetch

        with patch("src.exchange.binance_client.asyncio.sleep", side_effect=fake_sleep):
            with pytest.raises(RuntimeError):
                await client.fetch_ohlcv_with_retry("BTCUSDT", "4h", retries=1)

        captured = capfd.readouterr()
        output = captured.out + captured.err
        assert "fake_token_here" not in output
        assert "NetworkError" in output

    @pytest.mark.asyncio
    async def test_insufficient_funds_falha_imediatamente(self) -> None:
        """InsufficientFunds é erro fatal — não entra em retry."""
        client = _make_client()
        call_count = 0

        async def fake_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise ccxt.InsufficientFunds("no funds")

        client.fetch_ohlcv = fake_fetch

        with pytest.raises(ccxt.InsufficientFunds):
            await client.fetch_ohlcv_with_retry("BTCUSDT", "4h", retries=3)

        assert call_count == 1
