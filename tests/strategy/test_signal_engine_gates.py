from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import pytest

from src.strategy.plugin_base import NullSignalResult, SignalResult
from src.strategy.signal_engine import SignalEngine


@dataclass
class _DummyHandler:
    result: SignalResult

    async def evaluate(self, symbol: str, timeframe: str, df: pd.DataFrame) -> SignalResult:
        return self.result


@dataclass
class _DummyRegistry:
    handler: _DummyHandler

    def get(self, name: str) -> _DummyHandler | None:
        if name == "williams":
            return self.handler
        return None


def _df_latest(
    *,
    close: float = 100.0,
    jaw: float = 98.0,
    teeth: float = 99.0,
    lips: float = 100.5,
    ao: float = 1.0,
    fractal_high: float = 105.0,
    fractal_low: float = 97.0,
) -> pd.DataFrame:
    rows = []
    for i in range(49):
        rows.append(
            {
                "close": close,
                "jaw": jaw,
                "teeth": teeth,
                "lips": lips,
                "ao": ao,
                "fractal_high": fractal_high,
                "fractal_low": fractal_low,
                "idx": i,
            }
        )
    rows.append(
        {
            "close": close,
            "jaw": jaw,
            "teeth": teeth,
            "lips": lips,
            "ao": ao,
            "fractal_high": fractal_high,
            "fractal_low": fractal_low,
            "idx": 49,
        }
    )
    return pd.DataFrame(rows)


@pytest.mark.asyncio
async def test_gate_rejeita_regime_lateral() -> None:
    handler = _DummyHandler(
        SignalResult(
            direction="LONG",
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
            metadata={"plugin": "williams"},
        )
    )
    engine = SignalEngine(plugin_registry=_DummyRegistry(handler))
    df = _df_latest(jaw=100.0, teeth=100.0001, lips=100.0002, ao=0.0, fractal_low=99.0)

    result = await engine.evaluate("BTCUSDT", "15m", df)

    assert result.is_ok()
    payload = result.unwrap()
    assert isinstance(payload, NullSignalResult)
    assert payload.reason == "regime_lateral_blocked"


@pytest.mark.asyncio
async def test_gate_rejeita_checklist_bo_williams_incompleto() -> None:
    handler = _DummyHandler(
        SignalResult(
            direction="LONG",
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
            metadata={"plugin": "williams"},
        )
    )
    engine = SignalEngine(plugin_registry=_DummyRegistry(handler))
    # AO negativo invalida checklist LONG
    df = _df_latest(ao=-0.5)

    result = await engine.evaluate("BTCUSDT", "15m", df)

    assert result.is_ok()
    payload = result.unwrap()
    assert isinstance(payload, NullSignalResult)
    assert payload.reason.startswith("checklist_not_satisfied:")


@pytest.mark.asyncio
async def test_gate_aprova_signal_quando_checklist_ok() -> None:
    signal = SignalResult(
        direction="LONG",
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        metadata={"plugin": "williams"},
    )
    handler = _DummyHandler(signal)
    engine = SignalEngine(plugin_registry=_DummyRegistry(handler))
    df = _df_latest(ao=0.8, jaw=98.0, teeth=99.0, lips=100.0, close=101.0, fractal_low=97.0)

    result = await engine.evaluate("BTCUSDT", "15m", df)

    assert result.is_ok()
    payload = result.unwrap()
    assert isinstance(payload, SignalResult)
    assert payload.direction == "LONG"
