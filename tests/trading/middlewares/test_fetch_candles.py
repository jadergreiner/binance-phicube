from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from src.trading.middlewares.fetch_candles import FetchCandlesMiddleware
from src.trading.tick_pipeline import TickContext


@pytest.fixture
def mock_client():
    client = MagicMock()
    df = pd.DataFrame(
        {
            "timestamp": [1, 2, 3],
            "open": [100, 101, 102],
            "high": [110, 111, 112],
            "low": [90, 91, 92],
            "close": [105, 106, 107],
            "volume": [1000, 1100, 1200],
        }
    )
    client.fetch_ohlcv_with_retry = AsyncMock(return_value=df)
    return client


@pytest.fixture
def tick_context():
    return TickContext(symbol="BTCUSDT", timeframe="15m")


class TestFetchCandlesMiddleware:
    async def test_fetch_candles_success(self, mock_client, tick_context):
        middleware = FetchCandlesMiddleware(mock_client, warmup_candles=200)
        next_called = False

        async def next():
            nonlocal next_called
            next_called = True

        await middleware.process(tick_context, next)

        assert tick_context.df is not None
        assert len(tick_context.df) == 2  # 3 - 1 (last dropped)
        mock_client.fetch_ohlcv_with_retry.assert_called_once_with(
            symbol="BTCUSDT",
            timeframe="15m",
            limit=201,
        )
        assert next_called

    async def test_fetch_candles_error(self, mock_client, tick_context):
        mock_client.fetch_ohlcv_with_retry = AsyncMock(side_effect=Exception("Network error"))
        middleware = FetchCandlesMiddleware(mock_client, warmup_candles=200)
        next_called = False

        async def next():
            nonlocal next_called
            next_called = True

        with pytest.raises(Exception, match="Network error"):
            await middleware.process(tick_context, next)

        assert not next_called
