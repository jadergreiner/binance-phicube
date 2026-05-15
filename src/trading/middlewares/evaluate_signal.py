from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from src.common.serialization import SerializationFacade
from src.monitoring.logger import get_logger
from src.strategy.signal_engine import SignalResult
from src.trading.tick_pipeline import TickContext

logger = get_logger(__name__)


class EvaluateSignalMiddleware:
    """Middleware para avaliar sinais de trading."""

    def __init__(self, signal_engine: Any) -> None:
        self._signal_engine = signal_engine

    async def process(
        self,
        context: TickContext,
        next: Callable[[], Coroutine[Any, Any, None]],
    ) -> None:
        if context.df is None:
            context.abort("evaluate_signal_no_dataframe")
            return

        signal_result = await self._signal_engine.evaluate(
            context.symbol,
            context.timeframe,
            context.df,
        )

        # Persist signal evaluation
        consume = getattr(self._signal_engine, "consume_last_evaluation", None)
        if callable(consume):
            evaluation = consume()
            if evaluation is not None:
                payload = SerializationFacade.to_payload(evaluation)
                if isinstance(payload, dict):
                    repo = getattr(context, "_repo", None)
                    if repo is not None:
                        await repo.audit("signal_evaluated", payload)

        if not signal_result:
            context.abort("no_signal")
            return

        if not isinstance(signal_result, SignalResult):
            context.abort(f"invalid_signal_result_type: {type(signal_result).__name__}")
            return

        context.signal = signal_result
        await next()
