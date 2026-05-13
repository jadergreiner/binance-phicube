from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from src.monitoring.logger import get_logger
from src.notifications.events import NotificationEvent, TradeOpenedEvent
from src.trading.order_manager import TradeStatus
from src.trading.tick_pipeline import TickContext

logger = get_logger(__name__)


class NotifyMiddleware:
    """Middleware para enviar notificações de trades abertos."""

    def __init__(self, notifier: Any) -> None:
        self._notifier = notifier

    async def process(
        self,
        context: TickContext,
        next: Callable[[], Coroutine[Any, Any, None]],
    ) -> None:
        if context.trade is None:
            await next()
            return

        trade = context.trade
        if trade.status == TradeStatus.OPEN:
            await self._notifier.send(
                NotificationEvent.TRADE_OPENED,
                TradeOpenedEvent(
                    symbol=trade.symbol,
                    direction=trade.direction,
                    quantity=trade.quantity,
                    entry_price=trade.entry_price,
                    stop_loss=trade.stop_loss,
                    take_profit=trade.take_profit,
                    risk_amount=trade.risk_amount,
                    timestamp=trade.opened_at,
                ),
            )

        await next()
