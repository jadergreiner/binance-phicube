from __future__ import annotations

import asyncio
from typing import Any

import ccxt.async_support as ccxt
import pandas as pd

from src.config.settings import Settings
from src.monitoring.logger import get_logger

logger = get_logger(__name__)

# Mapping from simple notation (15m) to ccxt timeframe string
_TIMEFRAME_MAP: dict[str, str] = {
    "1m": "1m",
    "3m": "3m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "6h": "6h",
    "8h": "8h",
    "12h": "12h",
    "1d": "1d",
}


class BinanceClient:
    """Async wrapper around ccxt binanceusdm for Futures USDT-M."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        exchange_cls = ccxt.binanceusdm

        params: dict[str, Any] = {
            "apiKey": settings.binance_api_key,
            "secret": settings.binance_api_secret,
            "options": {"defaultType": "future"},
            "enableRateLimit": True,
        }

        if settings.binance_testnet:
            params["urls"] = {
                "api": {
                    "public": "https://testnet.binancefuture.com/fapi/v1",
                    "private": "https://testnet.binancefuture.com/fapi/v1",
                }
            }
            params["options"]["sandboxMode"] = True

        self._exchange: ccxt.binanceusdm = exchange_cls(params)

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    async def connect(self) -> None:
        await self._exchange.load_markets()
        logger.info("binance_client_connected", testnet=self._settings.binance_testnet)

    async def close(self) -> None:
        await self._exchange.close()
        logger.info("binance_client_closed")

    # ─── Market Data ──────────────────────────────────────────────────────────

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 200,
    ) -> pd.DataFrame:
        """Fetch OHLCV candles and return as DataFrame.

        Returns columns: [open_time, open, high, low, close, volume]
        The last (most recent) candle may be incomplete — callers should
        discard it when computing indicators.
        """
        tf = _TIMEFRAME_MAP.get(timeframe, timeframe)
        raw: list[list] = await self._exchange.fetch_ohlcv(symbol, tf, limit=limit)

        df = pd.DataFrame(raw, columns=["open_time", "open", "high", "low", "close", "volume"])
        df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        df = df.astype(
            {"open": float, "high": float, "low": float, "close": float, "volume": float}
        )
        return df

    async def fetch_balance(self) -> dict[str, Any]:
        """Return futures wallet balance."""
        balance = await self._exchange.fetch_balance({"type": "future"})
        return balance

    async def fetch_usdt_balance(self) -> float:
        balance = await self.fetch_balance()
        return float(balance.get("USDT", {}).get("free", 0.0))

    async def fetch_open_positions(self) -> list[dict[str, Any]]:
        """Return all open positions (non-zero)."""
        positions = await self._exchange.fetch_positions()
        return [p for p in positions if float(p.get("contracts", 0)) != 0]

    async def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        return await self._exchange.fetch_ticker(symbol)

    # ─── Order Management ─────────────────────────────────────────────────────

    async def set_leverage(self, symbol: str, leverage: int) -> None:
        try:
            await self._exchange.set_leverage(leverage, symbol)
            logger.info("leverage_set", symbol=symbol, leverage=leverage)
        except Exception as exc:
            logger.warning("leverage_set_failed", symbol=symbol, error=str(exc))

    async def set_margin_mode(self, symbol: str, mode: str = "isolated") -> None:
        """Set margin mode: 'isolated' or 'cross'."""
        try:
            await self._exchange.set_margin_mode(mode, symbol)
            logger.info("margin_mode_set", symbol=symbol, mode=mode)
        except Exception as exc:
            # Binance raises an error if mode is already set — safe to ignore
            logger.debug("margin_mode_already_set", symbol=symbol, error=str(exc))

    async def create_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a market order. side: 'buy' | 'sell'."""
        order = await self._exchange.create_market_order(
            symbol=symbol,
            side=side,
            amount=quantity,
            params=params or {},
        )
        logger.info(
            "market_order_created",
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_id=order.get("id"),
        )
        return order

    async def create_stop_loss_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
    ) -> dict[str, Any]:
        """Create a STOP_MARKET order for stop loss."""
        params = {
            "stopPrice": stop_price,
            "reduceOnly": True,
        }
        order = await self._exchange.create_order(
            symbol=symbol,
            type="STOP_MARKET",
            side=side,
            amount=quantity,
            params=params,
        )
        logger.info(
            "stop_loss_order_created",
            symbol=symbol,
            side=side,
            quantity=quantity,
            stop_price=stop_price,
            order_id=order.get("id"),
        )
        return order

    async def create_take_profit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        take_profit_price: float,
    ) -> dict[str, Any]:
        """Create a TAKE_PROFIT_MARKET order."""
        params = {
            "stopPrice": take_profit_price,
            "reduceOnly": True,
        }
        order = await self._exchange.create_order(
            symbol=symbol,
            type="TAKE_PROFIT_MARKET",
            side=side,
            amount=quantity,
            params=params,
        )
        logger.info(
            "take_profit_order_created",
            symbol=symbol,
            side=side,
            quantity=quantity,
            take_profit_price=take_profit_price,
            order_id=order.get("id"),
        )
        return order

    async def cancel_all_orders(self, symbol: str) -> None:
        try:
            await self._exchange.cancel_all_orders(symbol)
            logger.info("all_orders_cancelled", symbol=symbol)
        except Exception as exc:
            logger.warning("cancel_all_orders_failed", symbol=symbol, error=str(exc))

    # ─── Symbol Info ──────────────────────────────────────────────────────────

    def get_quantity_precision(self, symbol: str) -> int:
        """Return the quantity decimal precision for a symbol."""
        market = self._exchange.markets.get(symbol, {})
        precision = market.get("precision", {}).get("amount", 3)
        return int(precision)

    def get_price_precision(self, symbol: str) -> int:
        """Return the price decimal precision for a symbol."""
        market = self._exchange.markets.get(symbol, {})
        precision = market.get("precision", {}).get("price", 2)
        return int(precision)

    def round_quantity(self, symbol: str, qty: float) -> float:
        decimals = self.get_quantity_precision(symbol)
        return round(qty, decimals)

    def round_price(self, symbol: str, price: float) -> float:
        decimals = self.get_price_precision(symbol)
        return round(price, decimals)

    # ─── Retry helper ─────────────────────────────────────────────────────────

    async def fetch_ohlcv_with_retry(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 200,
        retries: int = 3,
        delay: float = 2.0,
    ) -> pd.DataFrame:
        last_exc: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                return await self.fetch_ohlcv(symbol, timeframe, limit)
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "fetch_ohlcv_retry",
                    symbol=symbol,
                    timeframe=timeframe,
                    attempt=attempt,
                    error=str(exc),
                )
                await asyncio.sleep(delay * attempt)
        raise RuntimeError(
            f"Failed to fetch OHLCV for {symbol}/{timeframe} after {retries} retries"
        ) from last_exc
