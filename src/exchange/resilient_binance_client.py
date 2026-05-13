"""ResilientBinanceClient: Facade pattern com Circuit Breaker para resiliência."""

from __future__ import annotations

import asyncio
from typing import Any

import pandas as pd

from src.config.settings import Settings
from src.exchange.binance_client import BinanceClient
from src.monitoring.logger import get_logger
from src.resilience import CircuitBreakerOpenError, CircuitBreakerRegistry, CircuitBreakerState

logger = get_logger(__name__)

DEFAULT_BINANCE_CALL_TIMEOUT_SECS: float = 2.0


class ResilientBinanceClient:
    """Facade: wrappeia BinanceClient com Circuit Breaker por método.

    Métodos críticos (Type A) levantam CircuitBreakerOpenError em CB OPEN.
    Métodos não-críticos (Type C) degradam gracefully.
    """

    def __init__(
        self,
        real_client: BinanceClient,
        settings: Settings,
        registry: CircuitBreakerRegistry | None = None,
    ) -> None:
        """Inicializa ResilientBinanceClient."""
        self._real_client = real_client
        self._settings = settings
        self._registry = registry or CircuitBreakerRegistry(namespace="binance")
        self._candle_cache: dict[tuple[str, str], pd.DataFrame] = {}

        recovery_timeout = max(
            10, settings.circuit_breaker_binance_recovery_timeout_secs
        )

        self._breaker_fetch_ohlcv = self._registry.get(
            "binance_fetch_ohlcv",
            recovery_timeout=float(recovery_timeout),
        )
        self._breaker_create_order = self._registry.get(
            "binance_create_order",
            recovery_timeout=float(recovery_timeout),
        )

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 200,
        since: int | None = None,
    ) -> pd.DataFrame:
        cache_key = (symbol, timeframe)
        self._breaker_fetch_ohlcv.attempt_half_open()

        if self._breaker_fetch_ohlcv.state == CircuitBreakerState.OPEN:
            if cache_key in self._candle_cache:
                return self._candle_cache[cache_key]
            return pd.DataFrame(
                columns=["open_time", "open", "high", "low", "close", "volume"]
            )

        try:
            df = await asyncio.wait_for(
                self._real_client.fetch_ohlcv(symbol, timeframe, limit, since),
                timeout=DEFAULT_BINANCE_CALL_TIMEOUT_SECS,
            )

            self._candle_cache[cache_key] = df
            self._breaker_fetch_ohlcv.record_success()
            return df

        except Exception:
            self._breaker_fetch_ohlcv.record_failure()

            if cache_key in self._candle_cache:
                return self._candle_cache[cache_key]

            return pd.DataFrame(
                columns=["open_time", "open", "high", "low", "close", "volume"]
            )

    async def create_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._breaker_create_order.attempt_half_open()

        if self._breaker_create_order.state == CircuitBreakerState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit Breaker OPEN para create_order({symbol}, {side}, {quantity})"
            )

        try:
            order = await asyncio.wait_for(
                self._real_client.create_market_order(symbol, side, quantity, params),
                timeout=DEFAULT_BINANCE_CALL_TIMEOUT_SECS,
            )

            self._breaker_create_order.record_success()
            return order

        except TimeoutError as exc:
            self._breaker_create_order.record_failure()
            raise RuntimeError(f"create_order timeout for {symbol}") from exc

        except Exception:
            self._breaker_create_order.record_failure()
            raise

    async def create_stop_loss(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
    ) -> dict[str, Any]:
        self._breaker_create_stop_loss.attempt_half_open()

        if self._breaker_create_stop_loss.state == CircuitBreakerState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit Breaker OPEN para create_stop_loss({symbol}, {side}, "
                f"{quantity}, {stop_price})"
            )

        try:
            order = await asyncio.wait_for(
                self._real_client.create_stop_loss_order(symbol, side, quantity, stop_price),
                timeout=DEFAULT_BINANCE_CALL_TIMEOUT_SECS,
            )

            self._breaker_create_stop_loss.record_success()
            return order

        except TimeoutError as exc:
            self._breaker_create_stop_loss.record_failure()
            raise RuntimeError(f"create_stop_loss timeout for {symbol}") from exc

        except Exception:
            self._breaker_create_stop_loss.record_failure()
            raise

    async def fetch_positions(self) -> list[dict[str, Any]]:
        self._breaker_fetch_positions.attempt_half_open()

        if self._breaker_fetch_positions.state == CircuitBreakerState.OPEN:
            raise CircuitBreakerOpenError("Circuit Breaker OPEN para fetch_positions()")

        try:
            positions = await asyncio.wait_for(
                self._real_client.fetch_open_positions(),
                timeout=DEFAULT_BINANCE_CALL_TIMEOUT_SECS,
            )

            self._breaker_fetch_positions.record_success()
            return positions

        except TimeoutError as exc:
            self._breaker_fetch_positions.record_failure()
            raise RuntimeError("fetch_positions timeout") from exc

        except Exception:
            self._breaker_fetch_positions.record_failure()
            raise

    async def fetch_balance(self) -> dict[str, Any]:
        return await self._real_client.fetch_balance()

    async def fetch_usdt_balance(self) -> float:
        return await self._real_client.fetch_usdt_balance()

    async def fetch_position_risk(
        self, *, symbol: str | None = None
    ) -> list[dict[str, Any]]:
        return await self._real_client.fetch_position_risk(symbol=symbol)

    async def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        return await self._real_client.fetch_ticker(symbol)

    async def validate_market_liquidity(
        self,
        symbol: str,
        min_volume: float | None = None,
        min_oi: float | None = None,
    ) -> None:
        kwargs = {"symbol": symbol}
        if min_volume is not None:
            kwargs["min_volume"] = min_volume
        if min_oi is not None:
            kwargs["min_oi"] = min_oi
        return await self._real_client.validate_market_liquidity(**kwargs)

    async def fetch_quantity_precision_map(self, symbols: list[str]) -> dict[str, int]:
        return await self._real_client.fetch_quantity_precision_map(symbols)

    async def set_leverage(self, symbol: str, leverage: int) -> None:
        await self._real_client.set_leverage(symbol, leverage)

    async def set_margin_mode(self, symbol: str, mode: str = "isolated") -> None:
        await self._real_client.set_margin_mode(symbol, mode)

    async def create_take_profit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        take_profit_price: float,
    ) -> dict[str, Any]:
        return await self._real_client.create_take_profit_order(
            symbol, side, quantity, take_profit_price
        )

    async def create_trailing_stop_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        activation_price: float,
        callback_rate: float,
    ) -> dict[str, Any]:
        return await self._real_client.create_trailing_stop_order(
            symbol, side, quantity, activation_price, callback_rate
        )

    async def cancel_all_orders(self, symbol: str) -> None:
        await self._real_client.cancel_all_orders(symbol)

    async def fetch_open_orders(self, symbol: str) -> list[dict[str, Any]]:
        return await self._real_client.fetch_open_orders(symbol)

    async def fetch_order(self, order_id: str, symbol: str) -> dict:
        return await self._real_client.fetch_order(order_id, symbol)

    def get_quantity_precision(self, symbol: str) -> int:
        return self._real_client.get_quantity_precision(symbol)

    def round_quantity(self, symbol: str, qty: float) -> float:
        return self._real_client.round_quantity(symbol, qty)

    def round_price(self, symbol: str, price: float) -> float:
        return self._real_client.round_price(symbol, price)

    async def fetch_ohlcv_with_retry(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 200,
        retries: int | None = None,
        base_delay: float | None = None,
    ) -> pd.DataFrame:
        return await self._real_client.fetch_ohlcv_with_retry(
            symbol, timeframe, limit, retries, base_delay
        )

    @property
    def registry(self) -> CircuitBreakerRegistry:
        return self._registry

    def get_breaker_state(self, method_name: str) -> str | None:
        if method_name == "fetch_ohlcv":
            return self._breaker_fetch_ohlcv.state.value
        elif method_name == "create_order":
            return self._breaker_create_order.state.value
        elif method_name == "create_stop_loss":
            return self._breaker_create_stop_loss.state.value
        elif method_name == "fetch_positions":
            return self._breaker_fetch_positions.state.value
        return None
