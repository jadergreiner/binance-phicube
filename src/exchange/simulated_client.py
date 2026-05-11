"""
Cliente Binance simulador (paper trading).

Usa dados reais da Binance para candles/preços (endpoints públicos,
acessíveis de qualquer região) e simula execução de ordens localmente.

Ideal para:
- Validação operacional sem Testnet (ex: Brasil com georestrição)
- Testes de integração sem depender de API keys de trade
- Soak test e auditoria de execuções (SPEC_023)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import ccxt.async_support as ccxt
import pandas as pd

from src.exchange.binance_client import (
    BinanceClient,
)
from src.monitoring.logger import get_logger

logger = get_logger(__name__)

_SLIPPAGE_PCT = 0.02  # 0.02% de slippage simulado


class SimulatedBinanceClient:
    """Substituto para BinanceClient que simula operações localmente.

    Usa BinanceClient real para dados públicos (OHLCV, ticker).
    Mantém estado interno para saldo, posições e ordens.

    Métodos não implementados levantam NotImplementedError para
    garantir que chamadas inesperadas sejam detectadas em desenvolvimento.
    """

    def __init__(
        self,
        real_client: BinanceClient,
        initial_balance_usdt: float = 10_000.0,
    ) -> None:
        self._real = real_client
        self._balance_usdt = initial_balance_usdt
        self._initial_balance = initial_balance_usdt

        # Estado interno: ordens simuladas {order_id: dict}
        self._orders: dict[str, dict[str, Any]] = {}

        # Estado interno: posições abertas {symbol: dict}
        self._positions: dict[str, dict[str, Any]] = {}

        # Contador para gerar IDs únicos
        self._order_counter = 0

        # Alavancagem por símbolo {symbol: leverage}
        self._leverage: dict[str, int] = {}

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Conecta o cliente real e tenta usar saldo real como referência."""
        await self._real.connect()
        try:
            real_balance = await self._real.fetch_usdt_balance()
            if real_balance > 0:
                self._balance_usdt = real_balance
                self._initial_balance = real_balance
        except Exception:
            logger.info(
                "simulated_client_fallback_balance",
                balance=self._balance_usdt,
            )
        logger.info(
            "simulated_client_started",
            initial_balance=self._balance_usdt,
        )

    async def close(self) -> None:
        await self._real.close()
        logger.info("simulated_client_closed")

    # ─── Market Data (delegado ao cliente real — endpoints públicos) ──────────

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 200,
        since: int | None = None,
    ) -> pd.DataFrame:
        """Delega ao cliente real (endpoint público)."""
        return await self._real.fetch_ohlcv(symbol, timeframe, limit, since)

    async def fetch_ohlcv_with_retry(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 200,
        retries: int | None = None,
        base_delay: float | None = None,
    ) -> pd.DataFrame:
        """Delega ao cliente real com retry."""
        return await self._real.fetch_ohlcv_with_retry(
            symbol,
            timeframe,
            limit,
            retries,
            base_delay,
        )

    async def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        """Delega ao cliente real (endpoint público)."""
        return await self._real.fetch_ticker(symbol)

    async def validate_market_liquidity(
        self,
        symbol: str,
        min_volume: float = 500_000.0,
        min_oi: float = 200_000.0,
    ) -> None:
        """Delega ao cliente real (usa dados públicos de ticker/OI)."""
        await self._real.validate_market_liquidity(symbol, min_volume, min_oi)

    async def fetch_quantity_precision_map(
        self,
        symbols: list[str],
    ) -> dict[str, int]:
        return await self._real.fetch_quantity_precision_map(symbols)

    def get_quantity_precision(self, symbol: str) -> int:
        return self._real.get_quantity_precision(symbol)

    def round_quantity(self, symbol: str, qty: float) -> float:
        return self._real.round_quantity(symbol, qty)

    def round_price(self, symbol: str, price: float) -> float:
        return self._real.round_price(symbol, price)

    # ─── Simulated Balance ───────────────────────────────────────────────────

    async def fetch_balance(self) -> dict[str, Any]:
        return {
            "USDT": {
                "free": self._balance_usdt,
                "used": 0.0,
                "total": self._balance_usdt,
            },
            "info": {"simulated": True},
        }

    async def fetch_usdt_balance(self) -> float:
        return self._balance_usdt

    # ─── Simulated Positions ─────────────────────────────────────────────────

    async def fetch_open_positions(self) -> list[dict[str, Any]]:
        return list(self._positions.values())

    async def fetch_position_risk(
        self,
        *,
        symbol: str | None = None,
    ) -> list[dict[str, Any]]:
        positions = list(self._positions.values())
        if symbol:
            target = symbol.upper().replace("/", "").replace(":", "")
            positions = [
                p
                for p in positions
                if p.get("symbol", "").upper().replace("/", "").replace(":", "") == target
            ]
        return positions

    # ─── Simulated Leverage ──────────────────────────────────────────────────

    async def set_leverage(self, symbol: str, leverage: int) -> None:
        self._leverage[symbol] = leverage
        logger.info(
            "simulated_leverage_set",
            symbol=symbol,
            leverage=leverage,
        )

    async def set_margin_mode(
        self,
        symbol: str,
        mode: str = "isolated",
    ) -> None:
        logger.debug(
            "simulated_margin_mode_set",
            symbol=symbol,
            mode=mode,
        )

    # ─── Simulated Order Management ──────────────────────────────────────────

    async def create_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Simula preenchimento imediato de ordem de mercado com slippage."""
        self._order_counter += 1
        order_id = f"sim_market_{self._order_counter}"

        ticker = await self._real.fetch_ticker(symbol)
        current_price = float(ticker.get("last") or ticker.get("close") or 0.0)

        slippage = current_price * _SLIPPAGE_PCT / 100.0
        fill_price = current_price + slippage if side == "buy" else current_price - slippage
        fill_price = round(fill_price, 2)

        cost = fill_price * quantity
        leverage = self._leverage.get(symbol, 1)
        margin_used = cost / leverage

        # Devolve margem se estiver reduzindo posição (fechamento parcial/total)
        pos_key = symbol.upper()
        existing_pos = self._positions.get(pos_key)
        if existing_pos:
            existing_side = existing_pos.get("side")
            is_reducing = (side == "sell" and existing_side == "long") or (
                side == "buy" and existing_side == "short"
            )
            if is_reducing:
                existing_qty = float(existing_pos.get("contracts", 0))
                existing_entry = float(existing_pos.get("entryPrice", 0))
                existing_margin = float(existing_pos.get("initialMargin", 0))
                reduce_ratio = min(quantity / max(existing_qty, 1e-8), 1.0)

                # Devolve margem proporcional
                self._balance_usdt += existing_margin * reduce_ratio

                # Realiza PnL da parcela fechada
                if existing_side == "long":
                    realized_pnl = (fill_price - existing_entry) * quantity * reduce_ratio
                else:
                    realized_pnl = (existing_entry - fill_price) * quantity * reduce_ratio
                self._balance_usdt += realized_pnl
            else:
                self._balance_usdt -= margin_used
        else:
            self._balance_usdt -= margin_used

        self._update_position(symbol, side, quantity, fill_price, leverage, current_price)

        order: dict[str, Any] = {
            "id": order_id,
            "symbol": symbol,
            "side": side,
            "type": "market",
            "quantity": quantity,
            "price": fill_price,
            "average": fill_price,
            "cost": cost,
            "filled": quantity,
            "remaining": 0.0,
            "status": "closed",
            "timestamp": datetime.now(UTC).isoformat(),
            "simulated": True,
        }
        self._orders[order_id] = order

        logger.info(
            "simulated_market_order_filled",
            symbol=symbol,
            side=side,
            quantity=quantity,
            fill_price=fill_price,
            order_id=order_id,
        )
        return order

    def _update_position(
        self,
        symbol: str,
        side: str,
        quantity: float,
        fill_price: float,
        leverage: int,
        current_price: float,
    ) -> None:
        """Atualiza estado interno de posição após execução simulada."""
        pos_key = symbol.upper()
        existing = self._positions.get(pos_key)

        if existing:
            old_qty = float(existing.get("contracts", 0))
            old_entry = float(existing.get("entryPrice", 0))
            side_mult = 1 if side == "buy" else -1
            new_qty = old_qty + quantity * side_mult

            if abs(new_qty) < 1e-8:
                self._positions.pop(pos_key, None)
                return

            if old_qty != 0:
                avg_entry = (old_qty * old_entry + quantity * fill_price) / (old_qty + quantity)
            else:
                avg_entry = fill_price

            self._positions[pos_key] = {
                "symbol": symbol,
                "contracts": abs(new_qty),
                "entryPrice": round(avg_entry, 2),
                "currentPrice": current_price,
                "unrealizedPnl": round(
                    (current_price - avg_entry) * abs(new_qty) * (1 if new_qty > 0 else -1),
                    2,
                ),
                "leverage": leverage,
                "side": "long" if new_qty > 0 else "short",
                "initialMargin": abs(new_qty) * current_price / leverage,
                "percentage": abs(new_qty) * current_price / max(self._balance_usdt, 1) * 100,
            }
        else:
            self._positions[pos_key] = {
                "symbol": symbol,
                "contracts": quantity,
                "entryPrice": round(fill_price, 2),
                "currentPrice": current_price,
                "unrealizedPnl": 0.0,
                "leverage": leverage,
                "side": "long" if side == "buy" else "short",
                "initialMargin": quantity * fill_price / max(leverage, 1),
                "percentage": quantity * fill_price / max(self._balance_usdt, 1) * 100,
            }

    async def create_stop_loss_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
    ) -> dict[str, Any]:
        """Cria ordem SL simulada (status open)."""
        self._order_counter += 1
        order_id = f"sim_sl_{self._order_counter}"
        order: dict[str, Any] = {
            "id": order_id,
            "symbol": symbol,
            "side": side,
            "type": "STOP_MARKET",
            "quantity": quantity,
            "stopPrice": stop_price,
            "price": stop_price,
            "average": 0.0,
            "filled": 0.0,
            "remaining": quantity,
            "status": "open",
            "reduceOnly": True,
            "timestamp": datetime.now(UTC).isoformat(),
            "simulated": True,
        }
        self._orders[order_id] = order
        logger.info(
            "simulated_sl_order_created",
            symbol=symbol,
            stop_price=stop_price,
            order_id=order_id,
        )
        return order

    async def create_take_profit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        take_profit_price: float,
    ) -> dict[str, Any]:
        """Cria ordem TP simulada (status open)."""
        self._order_counter += 1
        order_id = f"sim_tp_{self._order_counter}"
        order: dict[str, Any] = {
            "id": order_id,
            "symbol": symbol,
            "side": side,
            "type": "TAKE_PROFIT_MARKET",
            "quantity": quantity,
            "stopPrice": take_profit_price,
            "price": take_profit_price,
            "average": 0.0,
            "filled": 0.0,
            "remaining": quantity,
            "status": "open",
            "reduceOnly": True,
            "timestamp": datetime.now(UTC).isoformat(),
            "simulated": True,
        }
        self._orders[order_id] = order
        logger.info(
            "simulated_tp_order_created",
            symbol=symbol,
            tp_price=take_profit_price,
            order_id=order_id,
        )
        return order

    async def cancel_all_orders(self, symbol: str) -> None:
        """Cancela todas as ordens abertas simuladas do símbolo."""
        cancelled = [
            oid
            for oid, o in self._orders.items()
            if o.get("symbol") == symbol and o.get("status") == "open"
        ]
        for oid in cancelled:
            self._orders[oid]["status"] = "canceled"
        if cancelled:
            logger.info(
                "simulated_orders_cancelled",
                symbol=symbol,
                count=len(cancelled),
            )

    async def fetch_open_orders(self, symbol: str) -> list[dict[str, Any]]:
        """Retorna ordens abertas simuladas."""
        return [
            o
            for o in self._orders.values()
            if o.get("symbol") == symbol and o.get("status") == "open"
        ]

    async def fetch_order(
        self,
        order_id: str,
        symbol: str,
    ) -> dict[str, Any]:
        """Retorna ordem simulada pelo ID.

        Levanta ccxt.OrderNotFound se não existir (compatível com OrderMonitor).
        """
        order = self._orders.get(order_id)
        if order is None:
            raise ccxt.OrderNotFound(f"simulated order {order_id} not found")
        return order

    # ─── Resets ──────────────────────────────────────────────────────────────

    def reset(self, balance_usdt: float | None = None) -> None:
        """Reseta todo o estado simulado (saldo, ordens, posições)."""
        if balance_usdt is not None:
            self._balance_usdt = balance_usdt
            self._initial_balance = balance_usdt
        else:
            self._balance_usdt = self._initial_balance
        self._orders.clear()
        self._positions.clear()
        self._order_counter = 0
        logger.info("simulated_client_reset", balance=self._balance_usdt)

    @property
    def pnl_usdt(self) -> float:
        """PnL realizado atual (saldo atual - saldo inicial)."""
        return self._balance_usdt - self._initial_balance
