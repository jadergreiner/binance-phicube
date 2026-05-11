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
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from src.config.settings import ExitStrategy
from src.exchange.binance_client import BinanceClient
from src.monitoring.logger import get_logger
from src.notifications import Notifier
from src.notifications.events import NotificationEvent, SLProtectionFailedEvent
from src.strategy.signal_engine import Direction, Signal
from src.trading.risk_manager import PositionSize

logger = get_logger(__name__)


class TradeStatus(StrEnum):
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
    opened_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    closed_at: datetime | None = None
    pnl: float | None = None
    exit_price: float | None = None
    pnl_usdt: float | None = None
    close_reason: str | None = None
    signal: dict[str, Any] = field(default_factory=dict)
    exit_strategy: ExitStrategy | None = None
    tp_levels: list[dict[str, float]] | None = None
    tp_order_ids: list[str] | None = None

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
            "exit_price": self.exit_price,
            "pnl_usdt": self.pnl_usdt,
            "close_reason": self.close_reason,
            "signal": self.signal,
            "exit_strategy": self.exit_strategy.value if self.exit_strategy else None,
            "tp_levels": self.tp_levels,
            "tp_order_ids": self.tp_order_ids,
        }


class OrderManager:
    """Executes trades on Binance Futures based on validated signals."""

    def __init__(
        self,
        client: BinanceClient,
        leverage: int,
        notifier: Notifier | None = None,
        exit_strategy: ExitStrategy = ExitStrategy.FIXED,
        tp_levels: list[dict[str, float]] | None = None,
        trailing_activation_pct: float = 1.0,
        trailing_callback_rate: float = 0.5,
    ) -> None:
        self._client = client
        self._leverage = leverage
        self._notifier = notifier
        self._exit_strategy = exit_strategy
        self._tp_levels = tp_levels or [
            {"qty_pct": 50.0, "price_distance_pct": 2.0},
            {"qty_pct": 50.0, "price_distance_pct": 4.0},
        ]
        self._trailing_activation_pct = trailing_activation_pct
        self._trailing_callback_rate = trailing_callback_rate

    async def _create_sl_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
    ) -> dict[str, Any]:
        """Cria ordem STOP_MARKET (Stop Loss) e retorna o dict da ordem."""
        sl_price = self._client.round_price(symbol, stop_price)
        sl_order = await self._client.create_stop_loss_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            stop_price=sl_price,
        )
        sl_order_id = str(sl_order.get("id", "unknown"))
        logger.info(
            "sl_order_created",
            symbol=symbol,
            side=side,
            quantity=quantity,
            stop_price=sl_price,
            order_id=sl_order_id,
        )
        return sl_order

    async def _create_tp_orders(
        self,
        symbol: str,
        side: str,
        total_quantity: float,
        entry_price: float,
        tp_levels: list[dict[str, float]],
    ) -> list[str]:
        """Cria N ordens TAKE_PROFIT_MARKET para TP parcial.

        Para cada nível em tp_levels, calcula:
        - qty = total_quantity * qty_pct / 100
        - price = entry_price * (1 + price_distance_pct/100) para long
                 entry_price * (1 - price_distance_pct/100) para short

        Returns:
            Lista de order_ids criados

        Raises:
            Exception: se qualquer TP falhar (rollback será feito pelo caller)
        """
        is_long = side == "sell"  # TP side é oposto ao entry
        tp_order_ids: list[str] = []

        for i, level in enumerate(tp_levels):
            qty_pct = float(level["qty_pct"])
            price_dist_pct = float(level["price_distance_pct"])

            level_qty = total_quantity * qty_pct / 100.0
            level_qty = self._client.round_quantity(symbol, level_qty)

            if is_long:
                tp_price = entry_price * (1 + price_dist_pct / 100.0)
            else:
                tp_price = entry_price * (1 - price_dist_pct / 100.0)
            tp_price = self._client.round_price(symbol, tp_price)

            tp_order = await self._client.create_take_profit_order(
                symbol=symbol,
                side=side,
                quantity=level_qty,
                take_profit_price=tp_price,
            )
            tp_order_id = str(tp_order.get("id", "unknown"))
            tp_order_ids.append(tp_order_id)

            logger.info(
                "tp_order_created",
                symbol=symbol,
                level=i + 1,
                quantity=level_qty,
                tp_price=tp_price,
                qty_pct=qty_pct,
                order_id=tp_order_id,
            )

        return tp_order_ids

    @staticmethod
    def _calc_rrr_weighted(
        entry_price: float,
        stop_loss: float,
        tp_levels: list[dict[str, float]],
        direction: Direction,
    ) -> float:
        """Calcula RRR médio ponderado para trades com saída parcial (D-007).

        Cada nível de TP contribui proporcionalmente à sua fração da posição.
        direction é recebido para uso futuro em estratégias com assimetria long/short.
        """
        sl_distance_pct = abs(entry_price - stop_loss) / entry_price * 100.0

        weighted_rrr = 0.0
        for level in tp_levels:
            qty_pct = float(level["qty_pct"]) / 100.0
            price_dist_pct = float(level["price_distance_pct"])
            tp_distance_pct = price_dist_pct
            level_rrr = tp_distance_pct / sl_distance_pct if sl_distance_pct > 0 else 0
            weighted_rrr += level_rrr * qty_pct

        return round(weighted_rrr, 2)

    async def execute(self, signal: Signal, position: PositionSize) -> Trade | None:
        """Execute a full trade: market entry + SL + TP(s).

        If exit_strategy is "fixed" (default): single TP for full qty (legacy behavior).
        If exit_strategy is "partial": multiple TAKE_PROFIT_MARKET orders (SPEC_030).

        Returns a Trade object if successful, None on failure.
        """
        symbol = signal.symbol
        is_long = signal.direction == Direction.LONG
        entry_side = "buy" if is_long else "sell"
        exit_side = "sell" if is_long else "buy"
        total_qty = position.quantity

        # ─── Step 1: Configure leverage and margin mode ───────────────────────
        await self._client.set_leverage(symbol, self._leverage)
        await self._client.set_margin_mode(symbol, "isolated")

        # ─── Step 2: Market entry order ───────────────────────────────────────
        try:
            entry_order = await self._client.create_market_order(
                symbol=symbol,
                side=entry_side,
                quantity=total_qty,
            )
        except Exception as exc:
            logger.error(
                "entry_order_failed",
                symbol=symbol,
                error_type=type(exc).__name__,
            )
            return None

        entry_order_id = str(entry_order.get("id", "unknown"))
        actual_entry = float(entry_order.get("average") or position.entry_price)

        logger.info(
            "entry_executed",
            symbol=symbol,
            direction=signal.direction.value,
            quantity=total_qty,
            entry_price=actual_entry,
            order_id=entry_order_id,
        )

        # ─── Step 3: Stop Loss / Trailing Stop order (full quantity) ──────────
        sl_order_id: str | None = None
        try:
            if self._exit_strategy == ExitStrategy.TRAILING:
                # Trailing Stop replaces fixed SL
                if is_long:
                    activation_price = actual_entry * (1 + self._trailing_activation_pct / 100.0)
                else:
                    activation_price = actual_entry * (1 - self._trailing_activation_pct / 100.0)
                activation_price = self._client.round_price(symbol, activation_price)
                trailing_order = await self._client.create_trailing_stop_order(
                    symbol=symbol,
                    side=exit_side,
                    quantity=total_qty,
                    activation_price=activation_price,
                    callback_rate=self._trailing_callback_rate,
                )
                sl_order_id = str(trailing_order.get("id", "unknown"))
            else:
                sl_price = self._client.round_price(symbol, position.stop_loss)
                sl_order = await self._create_sl_order(
                    symbol=symbol,
                    side=exit_side,
                    quantity=total_qty,
                    stop_price=sl_price,
                )
                sl_order_id = str(sl_order.get("id", "unknown"))
        except Exception as exc:
            logger.error(
                "sl_order_failed",
                symbol=symbol,
                error_type=type(exc).__name__,
                action="cancelling_all_orders",
            )
            await self._client.cancel_all_orders(symbol)

            if self._notifier:
                await self._notifier.send(
                    NotificationEvent.SL_PROTECTION_FAILED,
                    SLProtectionFailedEvent(
                        symbol=symbol,
                        entry_order_id=entry_order_id,
                        entry_price=actual_entry,
                        quantity=total_qty,
                        timestamp=datetime.now(UTC),
                    ),
                )

            return _failed_trade(signal, position, entry_order_id)

        # ─── Step 4: Take Profit order(s) ────────────────────────────────────
        tp_order_ids: list[str] = []
        try:
            if self._exit_strategy == ExitStrategy.TRAILING:
                pass  # No fixed TP in trailing mode — exchange manages via trailing stop
            elif self._exit_strategy == ExitStrategy.PARTIAL and self._tp_levels:
                tp_order_ids = await self._create_tp_orders(
                    symbol=symbol,
                    side=exit_side,
                    total_quantity=total_qty,
                    entry_price=actual_entry,
                    tp_levels=self._tp_levels,
                )
            else:
                # Fixed: single TP for full quantity (legacy behavior)
                tp_price = self._client.round_price(symbol, position.take_profit)
                tp_order = await self._client.create_take_profit_order(
                    symbol=symbol,
                    side=exit_side,
                    quantity=total_qty,
                    take_profit_price=tp_price,
                )
                tp_order_id = str(tp_order.get("id", "unknown"))
                tp_order_ids = [tp_order_id]
                logger.info(
                    "tp_order_created",
                    symbol=symbol,
                    quantity=total_qty,
                    tp_price=tp_price,
                    order_id=tp_order_id,
                )
        except Exception as exc:
            logger.error(
                "tp_order_failed",
                symbol=symbol,
                error_type=type(exc).__name__,
                action="cancelling_all_orders",
            )
            await self._client.cancel_all_orders(symbol)
            return _failed_trade(signal, position, entry_order_id)

        # ─── Step 5: Build and return Trade ───────────────────────────────────
        trade = Trade(
            symbol=symbol,
            timeframe=signal.timeframe,
            direction=signal.direction,
            quantity=total_qty,
            entry_price=actual_entry,
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
            risk_amount=position.risk_amount,
            margin_used=position.margin_required,
            entry_order_id=entry_order_id,
            sl_order_id=sl_order_id,
            tp_order_id=tp_order_ids[0] if tp_order_ids else None,
            status=TradeStatus.OPEN,
            signal=signal.to_dict(),
            exit_strategy=self._exit_strategy,
            tp_levels=self._tp_levels,
            tp_order_ids=tp_order_ids,
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
