from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from src.strategy.signal_engine import SignalResult
from src.trading.middlewares.evaluate_signal import EvaluateSignalMiddleware
from src.trading.tick_pipeline import TickContext


@pytest.fixture
def mock_signal_engine():
    engine = MagicMock()
    engine.evaluate = AsyncMock(return_value=None)
    engine.consume_last_evaluation = MagicMock(return_value=None)
    return engine


@pytest.fixture
def tick_context():
    ctx = TickContext(symbol="BTCUSDT", timeframe="15m")
    ctx.df = pd.DataFrame({"close": [100, 101, 102]})
    return ctx


class TestEvaluateSignalMiddleware:
    async def test_no_signal(self, mock_signal_engine, tick_context):
        middleware = EvaluateSignalMiddleware(mock_signal_engine)
        next_called = False

        async def next():
            nonlocal next_called
            next_called = True

        await middleware.process(tick_context, next)

        assert tick_context.aborted
        assert tick_context.abort_reason == "no_signal"
        assert not next_called

    async def test_signal_found(self, mock_signal_engine, tick_context):
        signal_result = SignalResult(
            direction="LONG",
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
        )
        mock_signal_engine.evaluate = AsyncMock(return_value=signal_result)
        middleware = EvaluateSignalMiddleware(mock_signal_engine)
        next_called = False

        async def next():
            nonlocal next_called
            next_called = True

        await middleware.process(tick_context, next)

        assert not tick_context.aborted
        assert tick_context.signal == signal_result
        assert next_called

    async def test_invalid_signal_type(self, mock_signal_engine, tick_context):
        mock_signal_engine.evaluate = AsyncMock(return_value="invalid")
        middleware = EvaluateSignalMiddleware(mock_signal_engine)
        next_called = False

        async def next():
            nonlocal next_called
            next_called = True

        await middleware.process(tick_context, next)

        assert tick_context.aborted
        assert "invalid_signal_result_type" in tick_context.abort_reason
        assert not next_called
