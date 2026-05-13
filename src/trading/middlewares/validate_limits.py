from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from src.monitoring.logger import get_logger
from src.trading.tick_pipeline import TickContext

logger = get_logger(__name__)


class ValidateLimitsMiddleware:
    """Middleware para validar limites de posições abertas."""

    def __init__(self, repo: Any, max_open_positions: int) -> None:
        self._repo = repo
        self._max_open_positions = max_open_positions

    async def process(
        self,
        context: TickContext,
        next: Callable[[], Coroutine[Any, Any, None]],
    ) -> None:
        total_open = await self._repo.count_open_trades()
        if total_open >= self._max_open_positions:
            context.abort(f"max_positions_reached: {total_open}/{self._max_open_positions}")
            return

        symbol_trades = await self._repo.get_open_trades_for_symbol(context.symbol)
        if symbol_trades:
            context.abort(f"symbol_already_in_trade: {context.symbol}")
            return

        await next()
