"""Command para criar ordem de Take Profit."""

from __future__ import annotations

from typing import Any

from src.exchange.binance_client import BinanceClient
from src.monitoring.logger import get_logger
from src.trading.commands.base import Command

logger = get_logger(__name__)


class CreateTakeProfitCommand(Command):
    """Command para criar ordem TAKE_PROFIT_MARKET."""

    def __init__(
        self,
        client: BinanceClient,
        symbol: str,
        side: str,
        quantity: float,
        take_profit_price: float,
    ) -> None:
        super().__init__()
        self._client = client
        self._symbol = symbol
        self._side = side
        self._quantity = quantity
        self._take_profit_price = take_profit_price
        self._order_id: str | None = None

    async def execute(self) -> dict[str, Any]:
        """Cria ordem TP e retorna o dict da ordem."""
        try:
            tp_price = self._client.round_price(self._symbol, self._take_profit_price)
            order = await self._client.create_take_profit_order(
                symbol=self._symbol,
                side=self._side,
                quantity=self._quantity,
                take_profit_price=tp_price,
            )
            self._order_id = str(order.get("id", "unknown"))
            logger.info(
                "tp_order_created",
                symbol=self._symbol,
                side=self._side,
                quantity=self._quantity,
                tp_price=tp_price,
                order_id=self._order_id,
            )
            return self._mark_executed(order)
        except Exception as exc:
            self._mark_failed(exc)
            logger.error(
                "tp_order_failed",
                symbol=self._symbol,
                side=self._side,
                quantity=self._quantity,
                tp_price=self._take_profit_price,
                error_type=type(exc).__name__,
            )
            raise

    async def undo(self) -> None:
        """Cancela todas as ordens do símbolo para remover o TP."""
        if not self._executed or not self._order_id:
            return
        try:
            await self._client.cancel_all_orders(self._symbol)
            logger.info(
                "tp_order_cancelled",
                symbol=self._symbol,
                order_id=self._order_id,
            )
        except Exception as exc:
            logger.error(
                "tp_order_cancel_failed",
                symbol=self._symbol,
                order_id=self._order_id,
                error_type=type(exc).__name__,
            )
            raise
