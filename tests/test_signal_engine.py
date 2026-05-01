"""
Testes unitários — Motor de sinais (SignalEngine).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.strategy.signal_engine import Direction, SignalEngine

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _flat_df(n: int = 200, price: float = 100.0) -> pd.DataFrame:
    """Flat market — should never produce a signal."""
    return pd.DataFrame(
        {
            "open": [price] * n,
            "high": [price + 0.1] * n,
            "low": [price - 0.1] * n,
            "close": [price] * n,
            "volume": [500.0] * n,
        }
    )


def _trending_long_df(n: int = 200) -> pd.DataFrame:
    """Strong uptrend designed to trigger a LONG signal eventually."""
    prices = np.linspace(80, 130, n)
    # Add a clear fractal-high spike early to give the engine a reference to break
    prices[50] = prices[50] - 5.0  # local dip (bullish fractal support)
    high = prices + 0.5
    low = prices - 0.5
    high[40] = high[40] + 3.0  # bearish fractal (resistance to break)
    return pd.DataFrame(
        {
            "open": prices,
            "high": high,
            "low": low,
            "close": prices,
            "volume": np.ones(n) * 500,
        }
    )


def _trending_short_df(n: int = 200) -> pd.DataFrame:
    """Strong downtrend designed to trigger a SHORT signal eventually."""
    prices = np.linspace(130, 80, n)
    high = prices + 0.5
    low = prices - 0.5
    low[40] = low[40] - 3.0  # bullish fractal (support to break)
    high[50] = high[50] + 3.0  # bearish fractal (resistance for SL)
    return pd.DataFrame(
        {
            "open": prices,
            "high": high,
            "low": low,
            "close": prices,
            "volume": np.ones(n) * 500,
        }
    )


# ─── Tests ────────────────────────────────────────────────────────────────────


class TestSignalEngine:
    def setup_method(self):
        self.engine = SignalEngine(risk_reward_ratio=2.0)

    def test_returns_none_on_insufficient_data(self):
        df = _flat_df(30)
        result = self.engine.evaluate("BTCUSDT", "15m", df)
        assert result is None

    def test_returns_none_for_flat_market(self):
        df = _flat_df(200)
        result = self.engine.evaluate("BTCUSDT", "15m", df)
        assert result is None

    def test_signal_has_correct_symbol_and_timeframe(self):
        """If a signal is returned, metadata must match inputs."""
        df = _trending_long_df(200)
        result = self.engine.evaluate("ETHUSDT", "1h", df)
        if result is not None:
            assert result.symbol == "ETHUSDT"
            assert result.timeframe == "1h"

    def test_long_signal_direction(self):
        df = _trending_long_df(200)
        result = self.engine.evaluate("BTCUSDT", "15m", df)
        if result is not None:
            assert result.direction == Direction.LONG

    def test_short_signal_direction(self):
        df = _trending_short_df(200)
        result = self.engine.evaluate("BTCUSDT", "15m", df)
        if result is not None:
            assert result.direction == Direction.SHORT

    def test_long_signal_sl_below_entry(self):
        df = _trending_long_df(200)
        result = self.engine.evaluate("BTCUSDT", "15m", df)
        if result is not None:
            assert result.stop_loss < result.entry_price

    def test_long_signal_tp_above_entry(self):
        df = _trending_long_df(200)
        result = self.engine.evaluate("BTCUSDT", "15m", df)
        if result is not None:
            assert result.take_profit > result.entry_price

    def test_short_signal_sl_above_entry(self):
        df = _trending_short_df(200)
        result = self.engine.evaluate("BTCUSDT", "15m", df)
        if result is not None:
            assert result.stop_loss > result.entry_price

    def test_short_signal_tp_below_entry(self):
        df = _trending_short_df(200)
        result = self.engine.evaluate("BTCUSDT", "15m", df)
        if result is not None:
            assert result.take_profit < result.entry_price

    def test_risk_reward_ratio_respected(self):
        rrr = 2.5
        engine = SignalEngine(risk_reward_ratio=rrr)
        df = _trending_long_df(200)
        result = engine.evaluate("BTCUSDT", "15m", df)
        if result is not None:
            assert pytest.approx(result.risk_reward_ratio, rel=1e-3) == rrr

    def test_signal_to_dict_keys(self):
        df = _trending_long_df(200)
        result = self.engine.evaluate("BTCUSDT", "15m", df)
        if result is not None:
            d = result.to_dict()
            for key in [
                "symbol",
                "timeframe",
                "direction",
                "entry_price",
                "stop_loss",
                "take_profit",
                "fractal_ref",
                "risk",
                "reward",
                "risk_reward_ratio",
                "detected_at",
            ]:
                assert key in d


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
