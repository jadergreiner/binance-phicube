from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from src.monitoring.logger import get_logger
from src.trading.tick_pipeline import TickContext

logger = get_logger(__name__)


class FetchCandlesMiddleware:
    """Middleware para buscar candles OHLCV."""

    def __init__(self, client: Any, warmup_candles: int) -> None:
        self._client = client
        self._warmup_candles = warmup_candles

    async def process(
        self,
        context: TickContext,
        next: Callable[[], Coroutine[Any, Any, None]],
    ) -> None:
        df = await self._client.fetch_ohlcv_with_retry(
            symbol=context.symbol,
            timeframe=context.timeframe,
            limit=self._warmup_candles + 1,
        )
        # Discard the last (potentially incomplete) candle
        context.df = df.iloc[:-1].reset_index(drop=True)
        await next()
