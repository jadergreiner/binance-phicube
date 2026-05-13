"""
Testes unitários — Motor de sinais (SignalEngine).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.strategies.williams_strategy import WilliamsStrategy
from src.strategy.indicators import compute_all_optimized
from src.strategy.plugin_base import NullSignalResult, SignalResult
from src.strategy.plugin_registry import PluginRegistry
from src.strategy.signal_engine import SignalEngine

# ─── Engine fixture ────────────────────────────────────────────────────────────

_REGISTRY = PluginRegistry(plugin_timeout=2.0)
_REGISTRY.register("williams", WilliamsStrategy(risk_reward_ratio=2.0))
_ENGINE = SignalEngine(
    plugin_registry=_REGISTRY,
    default_strategy="williams",
    risk_reward_ratio=2.0,
)

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _flat_df(n: int = 200, price: float = 100.0) -> pd.DataFrame:
    """Flat market — should never produce a signal."""
    raw = pd.DataFrame(
        {
            "open": [price] * n,
            "high": [price + 0.1] * n,
            "low": [price - 0.1] * n,
            "close": [price] * n,
            "volume": [500.0] * n,
        }
    )
    return compute_all_optimized(raw)


def _trending_long_df(n: int = 200) -> pd.DataFrame:
    """Strong uptrend designed to trigger a LONG signal eventually."""
    prices = np.linspace(80, 130, n)
    prices[50] = prices[50] - 5.0  # local dip (bullish fractal support)
    high = prices + 0.5
    low = prices - 0.5
    high[40] = high[40] + 3.0  # bearish fractal (resistance to break)
    raw = pd.DataFrame(
        {
            "open": prices,
            "high": high,
            "low": low,
            "close": prices,
            "volume": np.ones(n) * 500,
        }
    )
    return compute_all_optimized(raw)


def _trending_short_df(n: int = 200) -> pd.DataFrame:
    """Strong downtrend designed to trigger a SHORT signal eventually."""
    prices = np.linspace(130, 80, n)
    high = prices + 0.5
    low = prices - 0.5
    low[40] = low[40] - 3.0  # bullish fractal (support to break)
    high[50] = high[50] + 3.0  # bearish fractal (resistance for SL)
    raw = pd.DataFrame(
        {
            "open": prices,
            "high": high,
            "low": low,
            "close": prices,
            "volume": np.ones(n) * 500,
        }
    )
    return compute_all_optimized(raw)


# ─── Tests ────────────────────────────────────────────────────────────────────


class TestSignalEngine:
    @pytest.mark.asyncio
    async def test_returns_nosignal_on_insufficient_data(self):
        df = _flat_df(30)
        result_obj = await _ENGINE.evaluate("BTCUSDT", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()
        assert isinstance(result, NullSignalResult)
        assert result.reason == "insufficient_candles"

    @pytest.mark.asyncio
    async def test_returns_nosignal_for_flat_market(self):
        df = _flat_df(200)
        result_obj = await _ENGINE.evaluate("BTCUSDT", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()
        assert isinstance(result, NullSignalResult)

    @pytest.mark.asyncio
    async def test_returns_nosignal_reason_for_insufficient_candles(self):
        df = _flat_df(30)
        result_obj = await _ENGINE.evaluate("BTCUSDT", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()
        assert isinstance(result, NullSignalResult)
        assert result.reason == "insufficient_candles"

    @pytest.mark.asyncio
    async def test_long_signal_direction(self):
        df = _trending_long_df(200)
        result_obj = await _ENGINE.evaluate("BTCUSDT", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()
        if isinstance(result, SignalResult):
            assert result.direction == "LONG"

    @pytest.mark.asyncio
    async def test_short_signal_direction(self):
        df = _trending_short_df(200)
        result_obj = await _ENGINE.evaluate("BTCUSDT", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()
        if isinstance(result, SignalResult):
            assert result.direction == "SHORT"

    @pytest.mark.asyncio
    async def test_long_signal_sl_below_entry(self):
        df = _trending_long_df(200)
        result_obj = await _ENGINE.evaluate("BTCUSDT", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()
        if isinstance(result, SignalResult):
            assert result.stop_loss < result.entry_price

    @pytest.mark.asyncio
    async def test_long_signal_tp_above_entry(self):
        df = _trending_long_df(200)
        result_obj = await _ENGINE.evaluate("BTCUSDT", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()
        if isinstance(result, SignalResult):
            assert result.take_profit > result.entry_price

    @pytest.mark.asyncio
    async def test_short_signal_sl_above_entry(self):
        df = _trending_short_df(200)
        result_obj = await _ENGINE.evaluate("BTCUSDT", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()
        if isinstance(result, SignalResult):
            assert result.stop_loss > result.entry_price

    @pytest.mark.asyncio
    async def test_short_signal_tp_below_entry(self):
        df = _trending_short_df(200)
        result_obj = await _ENGINE.evaluate("BTCUSDT", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()
        if isinstance(result, SignalResult):
            assert result.take_profit < result.entry_price

    @pytest.mark.asyncio
    async def test_risk_reward_ratio_respected(self):
        rrr = 2.5
        registry = PluginRegistry(plugin_timeout=2.0)
        registry.register("williams", WilliamsStrategy(risk_reward_ratio=rrr))
        engine = SignalEngine(plugin_registry=registry, risk_reward_ratio=rrr)
        df = _trending_long_df(200)
        result_obj = await engine.evaluate("BTCUSDT", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()
        if isinstance(result, SignalResult):
            realized = abs(result.take_profit - result.entry_price) / abs(
                result.entry_price - result.stop_loss
            )
            assert pytest.approx(realized, rel=1e-3) == rrr

    @pytest.mark.asyncio
    async def test_signal_result_fields(self):
        df = _trending_long_df(200)
        result_obj = await _ENGINE.evaluate("BTCUSDT", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()
        if isinstance(result, SignalResult):
            assert result.direction in ("LONG", "SHORT")
            assert result.entry_price > 0
            assert result.stop_loss > 0
            assert result.take_profit > 0

    @pytest.mark.asyncio
    async def test_no_signal_reason_is_descriptive(self):
        df = _flat_df(200)
        result_obj = await _ENGINE.evaluate("BTCUSDT", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()
        assert isinstance(result, NullSignalResult)
        assert bool(result.reason)  # reason must be non-empty

    @pytest.mark.asyncio
    async def test_engine_is_stateless_no_last_evaluation(self):
        import inspect

        assert not hasattr(_ENGINE, "_last_evaluation") or inspect.isroutine(
            getattr(_ENGINE, "_last_evaluation", None)
        )
        assert not hasattr(_ENGINE, "consume_last_evaluation") or inspect.isroutine(
            getattr(_ENGINE, "consume_last_evaluation", None)
        )


class TestAlligatorHelpers:
    def test_bullish_condition(self):
        from src.strategy.signal_engine import SignalEngine

        assert SignalEngine._is_alligator_bullish(10.0, 12.0, 14.0, 15.0) is True
        assert (
            SignalEngine._is_alligator_bullish(10.0, 12.0, 14.0, 13.0) is False
        )  # price below lips

    def test_bearish_condition(self):
        from src.strategy.signal_engine import SignalEngine

        assert SignalEngine._is_alligator_bearish(14.0, 12.0, 10.0, 9.0) is True
        assert (
            SignalEngine._is_alligator_bearish(14.0, 12.0, 10.0, 11.0) is False
        )  # price above lips
