from __future__ import annotations

import asyncio
import math
from typing import Any

import ccxt.async_support as ccxt
import pandas as pd

from src.config.settings import Settings
from src.monitoring.logger import get_logger

logger = get_logger(__name__)

LIQUIDITY_MIN_VOLUME_24H: float = 500_000.0
LIQUIDITY_MIN_OPEN_INTEREST: float = 200_000.0


class InsufficientLiquidityError(Exception):
    """Levantada quando um par não atinge os mínimos de liquidez exigidos."""


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
        # ccxt chama fetch_currencies() → api.binance.com/sapi/v1/margin/allPairs
        # (endpoint spot/margin desnecessário para USDT-M futures). Ignorar para evitar
        # falha quando api.binance.com não está acessível (testnet, VPN, firewall).
        async def _no_currencies(*_args, **_kwargs):
            return {}

        self._exchange.fetch_currencies = _no_currencies  # type: ignore[method-assign]
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
        since: int | None = None,
    ) -> pd.DataFrame:
        """Fetch OHLCV candles and return as DataFrame.

        Returns columns: [open_time, open, high, low, close, volume]
        The last (most recent) candle may be incomplete — callers should
        discard it when computing indicators.

        since: Unix timestamp em ms. None → candles mais recentes.
        """
        tf = _TIMEFRAME_MAP.get(timeframe, timeframe)
        raw: list[list] = await self._exchange.fetch_ohlcv(symbol, tf, since=since, limit=limit)

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

    async def fetch_position_risk(self, *, symbol: str | None = None) -> list[dict[str, Any]]:
        """Retorna position risk bruto (endpoint Binance Futures)."""
        params: dict[str, Any] = {}
        if symbol:
            market_symbol = symbol
            if "/" not in symbol:
                market_symbol = f"{symbol[:-4]}/USDT:USDT" if symbol.endswith("USDT") else symbol
            params["symbol"] = self._exchange.market_id(market_symbol)
        method = getattr(self._exchange, "fapiPrivateGetPositionRisk", None)
        if callable(method):
            raw = await method(params)
            if isinstance(raw, list):
                return raw
        # Fallback de compatibilidade (shape próximo, sem positionAmt garantido)
        return await self._exchange.fetch_positions([symbol] if symbol else None)

    async def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        return await self._exchange.fetch_ticker(symbol)

    async def validate_market_liquidity(
        self,
        symbol: str,
        min_volume: float = LIQUIDITY_MIN_VOLUME_24H,
        min_oi: float = LIQUIDITY_MIN_OPEN_INTEREST,
    ) -> None:
        """Levanta InsufficientLiquidityError se o par não atende mínimos (INV-018-03)."""
        ticker = await self._exchange.fetch_ticker(symbol)
        volume_24h = float(ticker.get("quoteVolume") or 0.0)
        if volume_24h < min_volume:
            raise InsufficientLiquidityError(
                f"{symbol}: volume_24h={volume_24h:.0f} USDT < mínimo {min_volume:.0f}"
            )

        reference_price = float(
            ticker.get("last") or ticker.get("close") or ticker.get("mark") or 0.0
        )
        try:
            oi_data = await self._exchange.fetch_open_interest(symbol)
            oi = float(oi_data.get("openInterestValue") or 0.0)
            if oi <= 0.0:
                oi_amount = float(oi_data.get("openInterestAmount") or 0.0)
                if oi_amount > 0.0 and reference_price > 0.0:
                    oi = oi_amount * reference_price
        except Exception as exc:
            logger.warning(
                "fetch_open_interest_failed",
                symbol=symbol,
                error_type=type(exc).__name__,
            )
            oi = 0.0
        if oi < min_oi:
            raise InsufficientLiquidityError(
                f"{symbol}: open_interest={oi:.0f} USDT < mínimo {min_oi:.0f}"
            )
        logger.info("market_liquidity_ok", symbol=symbol, volume_24h=volume_24h, oi=oi)

    async def fetch_quantity_precision_map(self, symbols: list[str]) -> dict[str, int]:
        """Retorna {symbol: casas_decimais} para cada símbolo solicitado."""
        markets = await self._exchange.load_markets()
        result: dict[str, int] = {}
        for s in symbols:
            if s in markets:
                precision = markets[s].get("precision", {}).get("amount", 0)
                result[s] = int(precision or 0)
        return result

    # ─── Order Management ─────────────────────────────────────────────────────

    async def set_leverage(self, symbol: str, leverage: int) -> None:
        try:
            await self._exchange.set_leverage(leverage, symbol)
            logger.info("leverage_set", symbol=symbol, leverage=leverage)
        except Exception as exc:
            logger.warning("leverage_set_failed", symbol=symbol, error_type=type(exc).__name__)

    async def set_margin_mode(self, symbol: str, mode: str = "isolated") -> None:
        """Set margin mode: 'isolated' or 'cross'."""
        try:
            await self._exchange.set_margin_mode(mode, symbol)
            logger.info("margin_mode_set", symbol=symbol, mode=mode)
        except Exception as exc:
            # Binance raises an error if mode is already set — safe to ignore
            logger.debug("margin_mode_already_set", symbol=symbol, error_type=type(exc).__name__)

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
            logger.warning("cancel_all_orders_failed", symbol=symbol, error_type=type(exc).__name__)

    async def fetch_open_orders(self, symbol: str) -> list[dict[str, Any]]:
        """Retorna ordens abertas (não preenchidas) para o símbolo."""
        orders = await self._exchange.fetch_open_orders(symbol)
        logger.debug("fetch_open_orders_ok", symbol=symbol, count=len(orders))
        return orders

    async def fetch_order(self, order_id: str, symbol: str) -> dict:
        """Busca detalhes de uma ordem pelo ID.

        Retorna o objeto de ordem ccxt, incluindo o campo `average`
        que representa o preço médio de execução real.
        Nunca loga str(exc) — usa type(exc).__name__ para evitar vazar credenciais.
        """
        order = await self._exchange.fetch_order(order_id, symbol)
        logger.debug(
            "fetch_order_ok",
            order_id=order_id,
            symbol=symbol,
            status=order.get("status"),
        )
        return order

    # ─── Symbol Info ──────────────────────────────────────────────────────────

    def get_quantity_precision(self, symbol: str) -> int:
        """Retorna casas decimais para quantidade, compatível com TICK_SIZE e DECIMAL_PLACES."""
        market = self._exchange.markets.get(symbol, {})
        amount = market.get("precision", {}).get("amount", 3)
        if amount is None:
            return 3
        famt = float(amount)
        if self._exchange.precisionMode == ccxt.TICK_SIZE:
            if famt <= 0:
                return 0
            if famt >= 1:
                return 0
            return max(0, -int(math.floor(math.log10(famt))))
        return int(famt)

    def round_quantity(self, symbol: str, qty: float) -> float:
        """Arredonda quantidade ao step size do símbolo via CCXT."""
        return float(self._exchange.amount_to_precision(symbol, qty))

    def round_price(self, symbol: str, price: float) -> float:
        """Arredonda preço ao tick size do símbolo via CCXT."""
        return float(self._exchange.price_to_precision(symbol, price))

    # ─── Retry helper ─────────────────────────────────────────────────────────

    async def fetch_ohlcv_with_retry(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 200,
        retries: int = 3,
        base_delay: float = 1.0,
    ) -> pd.DataFrame:
        """Retry com backoff exponencial apenas para erros recuperáveis.

        Delays: base_delay * 2^(attempt-1) → 1s, 2s, 4s com base_delay=1.0.
        Erros fatais (AuthenticationError, InsufficientFunds, BadSymbol,
        InvalidOrder) falham imediatamente sem retry.
        Nunca loga str(exc) — usa type(exc).__name__ para evitar vazar credenciais.
        """
        _FATAL = (
            ccxt.AuthenticationError,
            ccxt.InsufficientFunds,
            ccxt.BadSymbol,
            ccxt.InvalidOrder,
        )
        last_exc: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                return await self.fetch_ohlcv(symbol, timeframe, limit)
            except _FATAL:
                raise
            except Exception as exc:
                last_exc = exc
                next_delay = base_delay * (2 ** (attempt - 1))
                logger.warning(
                    "fetch_ohlcv_retry",
                    symbol=symbol,
                    timeframe=timeframe,
                    attempt=attempt,
                    retries=retries,
                    error_type=type(exc).__name__,
                    next_wait_s=next_delay,
                )
                await asyncio.sleep(next_delay)
        raise RuntimeError(
            f"Failed to fetch OHLCV for {symbol}/{timeframe} after {retries} retries"
        ) from last_exc
