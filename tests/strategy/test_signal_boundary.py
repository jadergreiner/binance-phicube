from __future__ import annotations

from unittest.mock import AsyncMock

import pandas as pd
import pytest

from src.common.result import err, ok
from src.strategy.plugin_base import NullSignalResult, SignalResult
from src.strategy.signal_boundary import (
    SignalEngineBoundaryAdapter,
    SignalEvaluationInput,
)


def _payload() -> SignalEvaluationInput:
    return SignalEvaluationInput(
        symbol="BTCUSDT",
        timeframe="15m",
        df=pd.DataFrame({"close": [1.0, 2.0, 3.0]}),
    )


@pytest.mark.asyncio
async def test_boundary_normaliza_signal_result() -> None:
    engine = type("Engine", (), {})()
    engine.evaluate = AsyncMock(
        return_value=SignalResult(
            direction="LONG",
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
        )
    )
    adapter = SignalEngineBoundaryAdapter(engine)

    output = await adapter.evaluate(_payload())

    assert output.has_signal is True
    assert output.decision == "LONG"
    assert output.signal_result is not None


@pytest.mark.asyncio
async def test_boundary_normaliza_null_signal() -> None:
    engine = type("Engine", (), {})()
    engine.evaluate = AsyncMock(return_value=NullSignalResult(reason="conditions_not_met"))
    adapter = SignalEngineBoundaryAdapter(engine)

    output = await adapter.evaluate(_payload())

    assert output.has_signal is False
    assert output.decision == "NO_SIGNAL"
    assert output.reason == "conditions_not_met"


@pytest.mark.asyncio
async def test_boundary_normaliza_result_ok() -> None:
    engine = type("Engine", (), {})()
    engine.evaluate = AsyncMock(
        return_value=ok(
            SignalResult(
                direction="SHORT",
                entry_price=100.0,
                stop_loss=105.0,
                take_profit=90.0,
            )
        )
    )
    adapter = SignalEngineBoundaryAdapter(engine)

    output = await adapter.evaluate(_payload())

    assert output.has_signal is True
    assert output.decision == "SHORT"


@pytest.mark.asyncio
async def test_boundary_result_err_retorna_no_signal() -> None:
    engine = type("Engine", (), {})()
    engine.evaluate = AsyncMock(return_value=err(Exception("boom")))
    adapter = SignalEngineBoundaryAdapter(engine)

    output = await adapter.evaluate(_payload())

    assert output.has_signal is False
    assert output.decision == "NO_SIGNAL"
    assert output.reason == "signal_engine_result_err"


@pytest.mark.asyncio
async def test_boundary_excecao_retorna_fallback_seguro() -> None:
    engine = type("Engine", (), {})()
    engine.evaluate = AsyncMock(side_effect=RuntimeError("broken"))
    adapter = SignalEngineBoundaryAdapter(engine)

    output = await adapter.evaluate(_payload())

    assert output.has_signal is False
    assert output.decision == "NO_SIGNAL"
    assert output.reason == "signal_engine_exception"
    assert output.error_type == "RuntimeError"
