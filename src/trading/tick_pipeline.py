from __future__ import annotations

import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any, Protocol

import pandas as pd

from src.trading.order_manager import Trade


@dataclass
class TickContext:
    """Contexto mutável durante execução do pipeline de tick."""

    symbol: str
    timeframe: str
    df: pd.DataFrame | None = None
    signal: Any | None = None  # Signal ou SignalResult
    position: Any | None = None  # PositionSize
    trade: Trade | None = None
    aborted: bool = False
    abort_reason: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)

    def abort(self, reason: str) -> None:
        self.aborted = True
        self.abort_reason = reason


class TickMiddleware(Protocol):
    """Protocolo para middlewares do pipeline de tick."""

    async def process(
        self,
        context: TickContext,
        next: Callable[[], Coroutine[Any, Any, None]],
    ) -> None: ...


class TickPipeline:
    """Pipeline de middlewares para processamento de ticks do TradingMonitor.

    Cada middleware pode abortar o pipeline ou continuar para o próximo.
    Métricas de duração e sucesso/abort são coletadas automaticamente.
    """

    def __init__(self) -> None:
        self._middlewares: list[TickMiddleware] = []

    def use(self, middleware: TickMiddleware) -> TickPipeline:
        self._middlewares.append(middleware)
        return self

    async def execute(self, context: TickContext) -> TickContext:
        index = 0

        async def next() -> None:
            nonlocal index
            if index < len(self._middlewares):
                middleware = self._middlewares[index]
                index += 1
                name = type(middleware).__name__
                start = time.time()
                try:
                    await middleware.process(context, next)
                    duration = time.time() - start
                    context.metrics.setdefault("middlewares", {})
                    context.metrics["middlewares"][name] = {
                        "duration": duration,
                        "success": True,
                        "aborted": False,
                    }
                except Exception as exc:
                    duration = time.time() - start
                    context.metrics.setdefault("middlewares", {})
                    context.metrics["middlewares"][name] = {
                        "duration": duration,
                        "success": False,
                        "aborted": True,
                        "error": type(exc).__name__,
                    }
                    if not context.aborted:
                        context.abort(f"{name}_error: {type(exc).__name__}")

        await next()
        return context
