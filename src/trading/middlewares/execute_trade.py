from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from src.monitoring.logger import get_logger
from src.trading.tick_pipeline import TickContext

logger = get_logger(__name__)


class ExecuteTradeMiddleware:
    """Middleware para executar trades."""

    def __init__(self, order_manager: Any, repo: Any) -> None:
        self._order_manager = order_manager
        self._repo = repo

    async def process(
        self,
        context: TickContext,
        next: Callable[[], Coroutine[Any, Any, None]],
    ) -> None:
        if context.signal is None or context.position is None:
            context.abort("execute_trade_missing_signal_or_position")
            return

        # Convert SignalResult to Signal if needed
        signal = context.signal
        if hasattr(signal, "direction") and not hasattr(signal, "entry_price"):
            pass
        else:
            from src.strategy.signal_engine import Direction, Signal

            signal = Signal(
                symbol=context.symbol,
                timeframe=context.timeframe,
                direction=Direction(signal.direction),
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                fractal_ref=(signal.metadata or {}).get("fractal_ref", 0.0)
                if hasattr(signal, "metadata")
                else 0.0,
            )

        trade = await self._order_manager.execute(signal, context.position)
        if trade is None:
            context.abort("order_manager_execute_returned_none")
            return

        trade_id = await self._repo.save_trade(trade)
        await self._repo.audit(
            "trade_opened",
            {"trade_id": trade_id, **trade.to_dict()},
        )

        context.trade = trade
        context.metrics["trade_id"] = trade_id
        context.metrics["trade_status"] = trade.status.value

        await next()
