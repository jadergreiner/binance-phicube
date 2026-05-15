"""Command para criar ordem de Stop Loss."""

from __future__ import annotations

from typing import Any

from src.config.settings import ExitStrategy
from src.exchange.base_client import TradingClient
from src.monitoring.logger import get_logger
from src.trading.commands.base import Command

logger = get_logger(__name__)


class CreateStopLossCommand(Command):
    """Command para criar ordem STOP_MARKET (Stop Loss) ou Trailing Stop."""

    def __init__(
        self,
        client: TradingClient,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
        exit_strategy: ExitStrategy = ExitStrategy.FIXED,
        trailing_activation_pct: float = 1.0,
        trailing_callback_rate: float = 0.5,
        entry_price: float = 0.0,
    ) -> None:
        super().__init__()
        self._client = client
        self._symbol = symbol
        self._side = side
        self._quantity = quantity
        self._stop_price = stop_price
        self._exit_strategy = exit_strategy
        self._trailing_activation_pct = trailing_activation_pct
        self._trailing_callback_rate = trailing_callback_rate
        self._entry_price = entry_price
        self._order_id: str | None = None

    async def execute(self) -> dict[str, Any]:
        """Cria ordem SL e retorna o dict da ordem."""
        try:
            if self._exit_strategy == ExitStrategy.TRAILING:
                is_long = self._side == "sell"
                if is_long:
                    activation_price = self._entry_price * (
                        1 + self._trailing_activation_pct / 100.0
                    )
                else:
                    activation_price = self._entry_price * (
                        1 - self._trailing_activation_pct / 100.0
                    )
                activation_price = self._client.round_price(self._symbol, activation_price)
                order = await self._client.create_trailing_stop_order(
                    symbol=self._symbol,
                    side=self._side,
                    quantity=self._quantity,
                    activation_price=activation_price,
                    callback_rate=self._trailing_callback_rate,
                )
            else:
                sl_price = self._client.round_price(self._symbol, self._stop_price)
                order = await self._client.create_stop_loss_order(
                    symbol=self._symbol,
                    side=self._side,
                    quantity=self._quantity,
                    stop_price=sl_price,
                )
            self._order_id = str(order.get("id", "unknown"))
            logger.info(
                "sl_order_created",
                symbol=self._symbol,
                side=self._side,
                quantity=self._quantity,
                stop_price=self._stop_price,
                order_id=self._order_id,
                exit_strategy=self._exit_strategy.value,
            )
            return self._mark_executed(order)
        except Exception as exc:
            self._mark_failed(exc)
            logger.error(
                "sl_order_failed",
                symbol=self._symbol,
                side=self._side,
                quantity=self._quantity,
                stop_price=self._stop_price,
                error_type=type(exc).__name__,
            )
            raise

    async def undo(self) -> None:
        """Cancela todas as ordens do símbolo para remover o SL."""
        if not self._executed or not self._order_id:
            return
        try:
            await self._client.cancel_all_orders(self._symbol)
            logger.info(
                "sl_order_cancelled",
                symbol=self._symbol,
                order_id=self._order_id,
            )
        except Exception as exc:
            logger.error(
                "sl_order_cancel_failed",
                symbol=self._symbol,
                order_id=self._order_id,
                error_type=type(exc).__name__,
            )
            raise
