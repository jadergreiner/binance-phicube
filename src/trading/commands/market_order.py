"""Command para criar ordem de mercado (entry)."""

from __future__ import annotations

from typing import Any

from src.exchange.binance_client import BinanceClient
from src.monitoring.logger import get_logger
from src.trading.commands.base import Command

logger = get_logger(__name__)


class CreateMarketOrderCommand(Command):
    """Command para criar ordem de mercado de entrada."""

    def __init__(
        self,
        client: BinanceClient,
        symbol: str,
        side: str,
        quantity: float,
    ) -> None:
        super().__init__()
        self._client = client
        self._symbol = symbol
        self._side = side
        self._quantity = quantity
        self._order_id: str | None = None

    async def execute(self) -> dict[str, Any]:
        """Cria ordem de mercado e retorna o dict da ordem."""
        try:
            order = await self._client.create_market_order(
                symbol=self._symbol,
                side=self._side,
                quantity=self._quantity,
            )
            self._order_id = str(order.get("id", "unknown"))
            logger.info(
                "market_order_executed",
                symbol=self._symbol,
                side=self._side,
                quantity=self._quantity,
                order_id=self._order_id,
            )
            return self._mark_executed(order)
        except Exception as exc:
            self._mark_failed(exc)
            logger.error(
                "market_order_failed",
                symbol=self._symbol,
                side=self._side,
                quantity=self._quantity,
                error_type=type(exc).__name__,
            )
            raise

    async def undo(self) -> None:
        """Cancela todas as ordens do símbolo se a entrada foi executada."""
        if not self._executed or not self._order_id:
            return
        try:
            await self._client.cancel_all_orders(self._symbol)
            logger.info(
                "market_order_cancelled",
                symbol=self._symbol,
                order_id=self._order_id,
            )
        except Exception as exc:
            logger.error(
                "market_order_cancel_failed",
                symbol=self._symbol,
                order_id=self._order_id,
                error_type=type(exc).__name__,
            )
            raise
