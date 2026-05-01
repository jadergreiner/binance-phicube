"""
Gerenciador de ordens — executa entradas e coloca SL/TP na Binance Futures.

Fluxo de execução:
    1. Configurar alavancagem e modo de margem (isolated)
    2. Enviar ordem de mercado de entrada
    3. Colocar STOP_MARKET (SL) e TAKE_PROFIT_MARKET (TP) como ordens OCO
    4. Persistir a operação no MongoDB

Em caso de falha ao colocar SL/TP, cancela todas as ordens abertas do símbolo
e registra o erro — nunca deixa uma posição sem proteção.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from src.exchange.binance_client import BinanceClient
from src.monitoring.logger import get_logger
from src.strategy.signal_engine import Direction, Signal
from src.trading.risk_manager import PositionSize

logger = get_logger(__name__)


class TradeStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED_TP = "CLOSED_TP"
    CLOSED_SL = "CLOSED_SL"
    CLOSED_MANUAL = "CLOSED_MANUAL"
    FAILED = "FAILED"


@dataclass
class Trade:
    symbol: str
    timeframe: str
    direction: Direction
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_amount: float
    margin_used: float
    entry_order_id: str
    sl_order_id: str | None = None
    tp_order_id: str | None = None
    status: TradeStatus = TradeStatus.OPEN
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: datetime | None = None
    pnl: float | None = None
    signal: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "direction": self.direction.value,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "risk_amount": self.risk_amount,
            "margin_used": self.margin_used,
            "entry_order_id": self.entry_order_id,
            "sl_order_id": self.sl_order_id,
            "tp_order_id": self.tp_order_id,
            "status": self.status.value,
            "opened_at": self.opened_at,
            "closed_at": self.closed_at,
            "pnl": self.pnl,
            "signal": self.signal,
        }


class OrderManager:
    """Executes trades on Binance Futures based on validated signals."""

    def __init__(self, client: BinanceClient, leverage: int) -> None:
        self._client = client
        self._leverage = leverage

    async def execute(self, signal: Signal, position: PositionSize) -> Trade | None:
        """Execute a full trade: market entry + SL + TP.

        Returns a Trade object if successful, None on failure.
        """
        symbol = signal.symbol
        is_long = signal.direction == Direction.LONG
        entry_side = "buy" if is_long else "sell"
        exit_side = "sell" if is_long else "buy"

        # ─── Step 1: Configure leverage and margin mode ───────────────────────
        await self._client.set_leverage(symbol, self._leverage)
        await self._client.set_margin_mode(symbol, "isolated")

        # ─── Step 2: Market entry order ───────────────────────────────────────
        try:
            entry_order = await self._client.create_market_order(
                symbol=symbol,
                side=entry_side,
                quantity=position.quantity,
            )
        except Exception as exc:
            logger.error("entry_order_failed", symbol=symbol, error=str(exc))
            return None

        entry_order_id = str(entry_order.get("id", "unknown"))
        actual_entry = float(entry_order.get("average") or position.entry_price)

        logger.info(
            "entry_executed",
            symbol=symbol,
            direction=signal.direction.value,
            quantity=position.quantity,
            entry_price=actual_entry,
            order_id=entry_order_id,
        )

        # ─── Step 3: Stop Loss order ──────────────────────────────────────────
        sl_order_id: str | None = None
        try:
            sl_price = self._client.round_price(symbol, position.stop_loss)
            sl_order = await self._client.create_stop_loss_order(
                symbol=symbol,
                side=exit_side,
                quantity=position.quantity,
                stop_price=sl_price,
            )
            sl_order_id = str(sl_order.get("id", "unknown"))
        except Exception as exc:
            logger.error(
                "sl_order_failed",
                symbol=symbol,
                error=str(exc),
                action="cancelling_all_orders",
            )
            await self._client.cancel_all_orders(symbol)
            return _failed_trade(signal, position, entry_order_id)

        # ─── Step 4: Take Profit order ────────────────────────────────────────
        tp_order_id: str | None = None
        try:
            tp_price = self._client.round_price(symbol, position.take_profit)
            tp_order = await self._client.create_take_profit_order(
                symbol=symbol,
                side=exit_side,
                quantity=position.quantity,
                take_profit_price=tp_price,
            )
            tp_order_id = str(tp_order.get("id", "unknown"))
        except Exception as exc:
            logger.error(
                "tp_order_failed",
                symbol=symbol,
                error=str(exc),
                action="cancelling_all_orders",
            )
            await self._client.cancel_all_orders(symbol)
            return _failed_trade(signal, position, entry_order_id)

        # ─── Step 5: Build and return Trade ───────────────────────────────────
        trade = Trade(
            symbol=symbol,
            timeframe=signal.timeframe,
            direction=signal.direction,
            quantity=position.quantity,
            entry_price=actual_entry,
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
            risk_amount=position.risk_amount,
            margin_used=position.margin_required,
            entry_order_id=entry_order_id,
            sl_order_id=sl_order_id,
            tp_order_id=tp_order_id,
            status=TradeStatus.OPEN,
            signal=signal.to_dict(),
        )

        logger.info("trade_opened", **trade.to_dict())
        return trade


def _failed_trade(signal: Signal, position: PositionSize, entry_order_id: str) -> Trade:
    return Trade(
        symbol=signal.symbol,
        timeframe=signal.timeframe,
        direction=signal.direction,
        quantity=position.quantity,
        entry_price=position.entry_price,
        stop_loss=position.stop_loss,
        take_profit=position.take_profit,
        risk_amount=position.risk_amount,
        margin_used=position.margin_required,
        entry_order_id=entry_order_id,
        status=TradeStatus.FAILED,
        signal=signal.to_dict(),
    )
