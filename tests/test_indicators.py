"""
Testes unitários — Indicadores técnicos (Alligator, AO, Fractais).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.strategy.indicators import (
    alligator,
    awesome_oscillator,
    fractals,
    last_valid_fractal_high,
    last_valid_fractal_low,
    smma,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_df(n: int = 100, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    high = close + rng.uniform(0.1, 1.0, n)
    low = close - rng.uniform(0.1, 1.0, n)
    open_ = close + rng.normal(0, 0.3, n)
    volume = rng.uniform(100, 1000, n)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume}
    )


# ─── SMMA ─────────────────────────────────────────────────────────────────────

class TestSMMA:
    def test_length_preserved(self):
        s = pd.Series(list(range(1, 51)), dtype=float)
        result = smma(s, 10)
        assert len(result) == 50

    def test_nan_before_period(self):
        s = pd.Series(list(range(1, 21)), dtype=float)
        result = smma(s, 10)
        # First valid value at index 9 (0-based)
        assert all(np.isnan(result.iloc[:9]))
        assert not np.isnan(result.iloc[9])

    def test_seed_equals_sma(self):
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = smma(s, 3)
        expected_seed = (1.0 + 2.0 + 3.0) / 3.0
        assert pytest.approx(result.iloc[2]) == expected_seed

    def test_convergence(self):
        """SMMA should converge to a stable value for a constant series."""
        s = pd.Series([10.0] * 50)
        result = smma(s, 5)
        # After seed, all values should be 10.0
        assert all(pytest.approx(v) == 10.0 for v in result.dropna())

    def test_insufficient_data(self):
        s = pd.Series([1.0, 2.0])
        result = smma(s, 5)
        assert all(np.isnan(result))


# ─── Alligator ────────────────────────────────────────────────────────────────

class TestAlligator:
    def test_columns_added(self):
        df = _make_df(100)
        out = alligator(df)
        assert "jaw" in out.columns
        assert "teeth" in out.columns
        assert "lips" in out.columns

    def test_original_columns_preserved(self):
        df = _make_df(50)
        out = alligator(df)
        for col in ["open", "high", "low", "close", "volume"]:
            assert col in out.columns

    def test_nan_in_warmup(self):
        df = _make_df(200)
        out = alligator(df)
        # With 13-period SMMA + 8-bar shift, jaw needs at least 21 rows
        assert out["jaw"].notna().any()

    def test_no_mutation_of_input(self):
        df = _make_df(100)
        original_cols = set(df.columns)
        alligator(df)
        assert set(df.columns) == original_cols


# ─── Awesome Oscillator ───────────────────────────────────────────────────────

class TestAO:
    def test_column_added(self):
        df = _make_df(50)
        out = awesome_oscillator(df)
        assert "ao" in out.columns

    def test_nan_before_period_34(self):
        df = _make_df(50)
        out = awesome_oscillator(df)
        # Rolling(34) needs 34 rows; index 33 is first valid
        assert all(np.isnan(out["ao"].iloc[:33]))
        assert out["ao"].notna().any()

    def test_sign_in_trending_market(self):
        """AO should be positive in a strongly upward trending market."""
        n = 100
        # Steadily rising prices
        prices = np.linspace(100, 200, n)
        df = pd.DataFrame(
            {"high": prices + 0.5, "low": prices - 0.5, "close": prices, "open": prices, "volume": 1.0}
        )
        out = awesome_oscillator(df)
        last_ao = out["ao"].dropna().iloc[-1]
        assert last_ao > 0


# ─── Fractais ─────────────────────────────────────────────────────────────────

class TestFractals:
    def test_columns_added(self):
        df = _make_df(50)
        out = fractals(df)
        assert "fractal_high" in out.columns
        assert "fractal_low" in out.columns

    def test_known_bearish_fractal(self):
        """Manually construct a clear bearish fractal at index 2."""
        highs = [1.0, 2.0, 5.0, 3.0, 1.5]
        lows = [0.5, 0.8, 0.9, 0.7, 0.6]
        df = pd.DataFrame(
            {"high": highs, "low": lows, "close": highs, "open": highs, "volume": 1.0}
        )
        out = fractals(df)
        assert out["fractal_high"].iloc[2] == 5.0
        assert np.isnan(out["fractal_high"].iloc[0])

    def test_known_bullish_fractal(self):
        """Manually construct a clear bullish fractal at index 2."""
        lows = [2.0, 1.5, 0.5, 1.8, 2.5]
        highs = [3.0, 2.5, 1.0, 2.8, 3.5]
        df = pd.DataFrame(
            {"high": highs, "low": lows, "close": highs, "open": highs, "volume": 1.0}
        )
        out = fractals(df)
        assert out["fractal_low"].iloc[2] == 0.5

    def test_last_two_rows_are_never_fractals(self):
        df = _make_df(100)
        out = fractals(df)
        assert np.isnan(out["fractal_high"].iloc[-1])
        assert np.isnan(out["fractal_high"].iloc[-2])
        assert np.isnan(out["fractal_low"].iloc[-1])
        assert np.isnan(out["fractal_low"].iloc[-2])

    def test_no_duplicate_fractal_high(self):
        """Two consecutive identical highs should not both be fractals."""
        highs = [1.0, 5.0, 5.0, 3.0, 1.5]
        lows = [0.5, 0.8, 0.9, 0.7, 0.6]
        df = pd.DataFrame(
            {"high": highs, "low": lows, "close": highs, "open": highs, "volume": 1.0}
        )
        out = fractals(df)
        assert np.isnan(out["fractal_high"].iloc[1])
        assert np.isnan(out["fractal_high"].iloc[2])


# ─── Fractal helpers ──────────────────────────────────────────────────────────

class TestFractalHelpers:
    def _df_with_fractals(self) -> pd.DataFrame:
        """Return a DataFrame with at least one bearish and bullish fractal."""
        # Insert a clear bearish fractal at index 50 and bullish at index 60
        n = 200
        rng = np.random.default_rng(0)
        close = 100 + np.cumsum(rng.normal(0, 0.5, n))
        high = close + 0.5
        low = close - 0.5

        # Force bearish fractal at 50
        high[50] = high[50] + 10.0

        # Force bullish fractal at 60
        low[60] = low[60] - 10.0

        df = pd.DataFrame(
            {"high": high, "low": low, "close": close, "open": close, "volume": 1.0}
        )
        return fractals(df)

    def test_last_valid_fractal_high_returns_float(self):
        df = self._df_with_fractals()
        result = last_valid_fractal_high(df)
        assert result is not None
        assert isinstance(result, float)

    def test_last_valid_fractal_low_returns_float(self):
        df = self._df_with_fractals()
        result = last_valid_fractal_low(df)
        assert result is not None
        assert isinstance(result, float)

    def test_empty_fractals_returns_none(self):
        n = 10
        df = pd.DataFrame(
            {
                "high": np.ones(n),
                "low": np.ones(n),
                "fractal_high": np.full(n, np.nan),
                "fractal_low": np.full(n, np.nan),
            }
        )
        assert last_valid_fractal_high(df) is None
        assert last_valid_fractal_low(df) is None
