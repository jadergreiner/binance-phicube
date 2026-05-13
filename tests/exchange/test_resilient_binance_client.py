"""Testes para ResilientBinanceClient com Circuit Breaker."""
import pytest
from unittest.mock import AsyncMock
from src.config.settings import SymbolConfig, Settings
from src.exchange.binance_client import BinanceClient
from src.exchange.resilient_binance_client import ResilientBinanceClient
from src.resilience import CircuitBreakerOpenError, CircuitBreakerRegistry, CircuitBreakerState
import pandas as pd


@pytest.fixture
def mock_settings() -> Settings:
    return Settings(
        binance_api_key="test_key",
        binance_api_secret="test_secret",
        binance_testnet=True,
        symbol_timeframes=[SymbolConfig.from_triplet("BTCUSDT:15m:5")],
        circuit_breaker_binance_recovery_timeout_secs=30,
    )


@pytest.fixture
def mock_binance_client() -> AsyncMock:
    return AsyncMock(spec=BinanceClient)


@pytest.fixture
def registry() -> CircuitBreakerRegistry:
    return CircuitBreakerRegistry(namespace="binance_test")


@pytest.fixture
def resilient_client(
    mock_binance_client: AsyncMock,
    mock_settings: Settings,
    registry: CircuitBreakerRegistry,
) -> ResilientBinanceClient:
    return ResilientBinanceClient(
        real_client=mock_binance_client,
        settings=mock_settings,
        registry=registry,
    )


class TestInitialization:
    def test_initialization_with_registry(
        self,
        mock_binance_client: AsyncMock,
        mock_settings: Settings,
        registry: CircuitBreakerRegistry,
    ) -> None:
        client = ResilientBinanceClient(mock_binance_client, mock_settings, registry)
        assert client._real_client is mock_binance_client
        assert client._registry is registry

    def test_timeout_from_config(self, resilient_client: ResilientBinanceClient) -> None:
        assert resilient_client._breaker_fetch_ohlcv.recovery_timeout == 30.0


class TestFetchOhlcvGracefulDegrade:
    @pytest.mark.asyncio
    async def test_success_updates_cache(
        self,
        resilient_client: ResilientBinanceClient,
        mock_binance_client: AsyncMock,
    ) -> None:
        df = pd.DataFrame({"open": [1.0], "close": [1.5]})
        mock_binance_client.fetch_ohlcv.return_value = df

        result = await resilient_client.fetch_ohlcv("BTCUSDT", "15m")

        assert result is df
        assert ("BTCUSDT", "15m") in resilient_client._candle_cache
        assert resilient_client._breaker_fetch_ohlcv.failure_count == 0

    @pytest.mark.asyncio
    async def test_failure_returns_cache(
        self,
        resilient_client: ResilientBinanceClient,
        mock_binance_client: AsyncMock,
    ) -> None:
        cached_df = pd.DataFrame({"open": [1.0], "close": [1.5]})
        resilient_client._candle_cache[("BTCUSDT", "15m")] = cached_df
        mock_binance_client.fetch_ohlcv.side_effect = RuntimeError("API error")

        result = await resilient_client.fetch_ohlcv("BTCUSDT", "15m")

        assert result is cached_df
        assert resilient_client._breaker_fetch_ohlcv.failure_count == 1


class TestCreateOrderFastFail:
    @pytest.mark.asyncio
    async def test_cb_open_raises_immediately(
        self,
        resilient_client: ResilientBinanceClient,
        mock_binance_client: AsyncMock,
    ) -> None:
        resilient_client._breaker_create_order.failure_threshold = 1
        resilient_client._breaker_create_order.record_failure()

        with pytest.raises(CircuitBreakerOpenError):
            await resilient_client.create_order("BTCUSDT", "buy", 1.0)

        mock_binance_client.create_market_order.assert_not_called()


class TestCircuitBreakerTransitions:
    def test_closed_to_open_transition(
        self,
        resilient_client: ResilientBinanceClient,
    ) -> None:
        breaker = resilient_client._breaker_fetch_ohlcv
        breaker.failure_threshold = 3

        assert breaker.state == CircuitBreakerState.CLOSED

        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitBreakerState.CLOSED

        breaker.record_failure()
        assert breaker.state == CircuitBreakerState.OPEN
        assert breaker.failure_count == 3


class TestIntrospection:
    def test_get_breaker_state(self, resilient_client: ResilientBinanceClient) -> None:
        assert resilient_client.get_breaker_state("fetch_ohlcv") == "closed"
