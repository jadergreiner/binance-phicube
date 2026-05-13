from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any, Protocol

from src.trading.tick_pipeline import TickContext


class TickMiddleware(Protocol):
    """Protocolo para middlewares do pipeline de tick."""

    async def process(
        self,
        context: TickContext,
        next: Callable[[], Coroutine[Any, Any, None]],
    ) -> None: ...
