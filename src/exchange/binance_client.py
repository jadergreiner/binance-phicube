from __future__ import annotations

import asyncio  # noqa: F401 — patch target for tests: src.exchange.binance_client.asyncio.sleep
import math
from typing import Any

import ccxt.async_support as ccxt
import pandas as pd

from src.common.decorators import retry
from src.config.settings import Settings
from src.exchange.base_client import TradingClient
from src.monitoring.logger import get_logger

logger = get_logger(__name__)

LIQUIDITY_MIN_VOLUME_24H: float = 500_000.0
LIQUIDITY_MIN_OPEN_INTEREST: float = 200_000.0

# Erros fatais para fetch_ohlcv — re-raise imediato sem retry
_FATAL_OHLCV_EXC_TYPES: tuple[type[BaseException], ...] = (
    ccxt.AuthenticationError,
    ccxt.InsufficientFunds,
    ccxt.BadSymbol,
    ccxt.InvalidOrder,
)

# Número padrão de tentativas para fetch_ohlcv
_DEFAULT_OHLCV_RETRIES: int = 3
_DEFAULT_OHLCV_INITIAL_DELAY: float = 1.0
_DEFAULT_OHLCV_BACKOFF_FACTOR: float = 2.0


def _ohlcv_exception_wrapper(
    exc: BaseException,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    bound_args: dict[str, Any],
) -> Exception:
    """Wrapper para exceção final do fetch_ohlcv.

    Usa bound_args para acessar symbol e timeframe da chamada original.
    """
    symbol = bound_args.get("symbol", "unknown")
    timeframe = bound_args.get("timeframe", "unknown")
    return RuntimeError(
        f"Failed to fetch OHLCV for {symbol}/{timeframe} after {_DEFAULT_OHLCV_RETRIES} retries"
    )


class InsufficientLiquidityError(Exception):
    """Levantada quando um par não atinge os mínimos de liquidez exigidos."""

    def __init__(self, message: str, reason_code: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


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


class BinanceClient(TradingClient):
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
        method = getattr(self._exchange, "fapiPrivateV3GetPositionRisk", None)
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
                f"{symbol}: volume_24h={volume_24h:.0f} USDT < mínimo {min_volume:.0f}",
                reason_code="insufficient_volume",
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
                f"{symbol}: open_interest={oi:.0f} USDT < mínimo {min_oi:.0f}",
                reason_code="insufficient_open_interest",
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

    async def _create_order_with_protect(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        params: dict[str, Any],
        log_warn_event: str,
        log_info_event: str,
        log_info_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Template Method: cria ordem com priceProtect e fallback silencioso (SPEC_043).

        Tenta criar a ordem com priceProtect=True. Se a exchange rejeitar
        com BadRequest (ex: testnet ou par sem suporte), retry sem priceProtect.
        """
        params_with_protect = {**params, "priceProtect": True}
        try:
            order = await self._exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                params=params_with_protect,
            )
        except ccxt.BadRequest:
            order = await self._exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                params=params.copy(),
            )
            logger.warning(log_warn_event, symbol=symbol, side=side)

        extra = (log_info_fields or {}) | {"order_id": order.get("id")}
        logger.info(log_info_event, symbol=symbol, side=side, amount=amount, **extra)
        return order

    async def create_stop_loss_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
    ) -> dict[str, Any]:
        """Create a STOP_MARKET order for stop loss with priceProtect (SPEC_043)."""
        return await self._create_order_with_protect(
            symbol=symbol,
            order_type="STOP_MARKET",
            side=side,
            amount=quantity,
            params={"stopPrice": stop_price, "reduceOnly": True},
            log_warn_event="priceProtect_not_supported_stop_loss",
            log_info_event="stop_loss_order_created",
            log_info_fields={"stop_price": stop_price},
        )

    async def create_take_profit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        take_profit_price: float,
    ) -> dict[str, Any]:
        """Create a TAKE_PROFIT_MARKET order with priceProtect (SPEC_043)."""
        return await self._create_order_with_protect(
            symbol=symbol,
            order_type="TAKE_PROFIT_MARKET",
            side=side,
            amount=quantity,
            params={"stopPrice": take_profit_price, "reduceOnly": True},
            log_warn_event="priceProtect_not_supported_take_profit",
            log_info_event="take_profit_order_created",
            log_info_fields={"take_profit_price": take_profit_price},
        )

    async def create_trailing_stop_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        activation_price: float,
        callback_rate: float,
    ) -> dict[str, Any]:
        """Create a TRAILING_STOP_MARKET order via Algo Order API.

        Uses ccxt's native trailingPercent support. ccxt routes to POST /fapi/v1/algo.
        ⚠️ closePosition=True causes error -4136 — uses explicit quantity + reduceOnly.
        priceProtect tentado com fallback silencioso (SPEC_043).
        """
        return await self._create_order_with_protect(
            symbol=symbol,
            order_type="TRAILING_STOP_MARKET",
            side=side,
            amount=quantity,
            params={
                "trailingPercent": callback_rate,
                "trailingTriggerPrice": activation_price,
                "reduceOnly": True,
            },
            log_warn_event="priceProtect_not_supported_trailing_stop",
            log_info_event="trailing_stop_order_created",
            log_info_fields={
                "activation_price": activation_price,
                "callback_rate": callback_rate,
            },
        )

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

    async def fetch_order(self, order_id: str, symbol: str) -> dict[str, Any]:
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

    @retry(
        max_attempts=_DEFAULT_OHLCV_RETRIES,
        initial_delay=_DEFAULT_OHLCV_INITIAL_DELAY,
        backoff_factor=_DEFAULT_OHLCV_BACKOFF_FACTOR,
        exc_types=(Exception,),
        fatal_exc_types=_FATAL_OHLCV_EXC_TYPES,
        exception_wrapper=_ohlcv_exception_wrapper,
        log_event_prefix="fetch_ohlcv",
    )
    async def _fetch_ohlcv_core(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 200,
    ) -> pd.DataFrame:
        """Método interno decorado com @retry para fetch_ohlcv.

        Não use diretamente — use fetch_ohlcv_with_retry() para compatibilidade.
        """
        return await self.fetch_ohlcv(symbol, timeframe, limit)

    async def fetch_ohlcv_with_retry(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 200,
        retries: int | None = None,
        base_delay: float | None = None,
    ) -> pd.DataFrame:
        """Retry com backoff exponencial para erros recuperáveis.

        Usa @retry decorador centralizado de src.common.decorators.

        Parâmetros DEPRECADOS (mantidos para compatibilidade):
        - retries: Ignorado — usa padrão {_DEFAULT_OHLCV_RETRIES} tentativas
        - base_delay: Ignorado — usa padrão {_DEFAULT_OHLCV_INITIAL_DELAY}s

        Comportamento:
        - Backoff exponencial: 1s, 2s, 4s
        - Erros fatais (AuthenticationError, InsufficientFunds, BadSymbol,
          InvalidOrder) falham imediatamente sem retry
        - Nunca loga str(exc) — usa error_type=type(exc).__name__

        Args:
            symbol: Par de trading (ex: BTCUSDT)
            timeframe: Período (ex: 4h, 15m)
            limit: Número de candles para buscar
            retries: DEPRECATED — ignorado
            base_delay: DEPRECATED — ignorado

        Returns:
            DataFrame com candles OHLCV

        Raises:
            RuntimeError: Quando tentativas se esgotam
            ccxt.AuthenticationError, ccxt.InsufficientFunds, etc: Erros fatais
        """
        # Aviso se parâmetros deprecated forem usados
        if retries is not None or base_delay is not None:
            logger.debug(
                "fetch_ohlcv_deprecated_params_ignored",
                retries=retries,
                base_delay=base_delay,
            )

        return await self._fetch_ohlcv_core(symbol, timeframe, limit)
