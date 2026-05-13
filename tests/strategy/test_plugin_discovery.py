"""
Testes SPEC_033 — WilliamsStrategy + Decorators (TEST_033_07 a 12).

Verifica:
    - WilliamsStrategy: sinais LONG/SHORT/None, fractal caching, confidence
    - TimeoutDecorator: timeout retorna NullSignalResult
    - ValidationDecorator: SL/TP inválidos
    - MetricsDecorator: métricas chamadas
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.strategies.williams_strategy import WilliamsStrategy
from src.strategy.plugin_base import NullSignalResult, SignalResult
from src.strategy.plugin_decorator import (
    MetricsDecorator,
    TimeoutDecorator,
    ValidationDecorator,
)


def _make_bullish_df(n: int = 50) -> pd.DataFrame:
    """DataFrame com alligator bullish e AO > 0."""
    np.random.seed(42)
    close = np.linspace(100, 110, n) + np.random.randn(n) * 0.5
    high = close + np.random.rand(n) * 2.0 + 1.0
    low = close - np.random.rand(n) * 2.0 - 1.0
    close[-3:] = [109.0, 109.5, 110.0]
    high[-3:] = [110.0, 110.5, 111.0]
    low[-3:] = [108.0, 108.2, 108.5]

    df = pd.DataFrame(
        {"open": close * 0.99, "high": high, "low": low, "close": close, "volume": 1000}
    )

    # Alligator bullish (lips > teeth > jaw, close > lips)
    df["jaw"] = 104.0
    df["teeth"] = 105.0
    df["lips"] = 106.0
    df["ao"] = 2.5

    # Fractais: fractal_high visível e fractal_low abaixo do close
    df["fractal_high"] = np.nan
    df["fractal_low"] = np.nan
    df.loc[df.index[-3], "fractal_high"] = 107.0
    df.loc[df.index[-4], "fractal_low"] = 103.0

    # ATR
    df["atr"] = 1.5

    return df


def _make_bearish_df(n: int = 50) -> pd.DataFrame:
    """DataFrame com alligator bearish e AO < 0."""
    np.random.seed(42)
    close = np.linspace(110, 100, n) + np.random.randn(n) * 0.5
    high = close + np.random.rand(n) * 2.0 + 1.0
    low = close - np.random.rand(n) * 2.0 - 1.0
    close[-3:] = [101.0, 100.5, 100.0]
    high[-3:] = [102.0, 101.5, 101.0]
    low[-3:] = [99.0, 99.2, 99.0]

    df = pd.DataFrame(
        {"open": close * 1.01, "high": high, "low": low, "close": close, "volume": 1000}
    )

    # Alligator bearish (lips < teeth < jaw, close < lips)
    df["jaw"] = 109.0
    df["teeth"] = 108.0
    df["lips"] = 107.0
    df["ao"] = -2.5

    # Fractais
    df["fractal_high"] = np.nan
    df["fractal_low"] = np.nan
    df.loc[df.index[-3], "fractal_high"] = 108.0
    df.loc[df.index[-4], "fractal_low"] = 105.0

    df["atr"] = 1.5

    return df


def _make_no_signal_df(n: int = 50) -> pd.DataFrame:
    """DataFrame sem condições de sinal (alligator dormindo)."""
    close = np.full(n, 100.0)
    df = pd.DataFrame(
        {"open": close, "high": close + 2, "low": close - 2, "close": close, "volume": 1000}
    )
    # Alligator dormindo: lips < teeth < jaw mas AO ~ 0 e fractais não rompidos
    df["jaw"] = 102.0
    df["teeth"] = 101.0
    df["lips"] = 100.0  # bearish structure, mas AO ~ 0
    df["ao"] = 0.0
    df["fractal_high"] = np.nan
    df["fractal_low"] = np.nan
    df.loc[df.index[-3], "fractal_high"] = 103.0
    df.loc[df.index[-4], "fractal_low"] = 98.0
    df["atr"] = 1.0
    return df


# ─── TEST_033_07: WilliamsStrategy ────────────────────────────────────────────


class TestWilliamsStrategy:
    async def test_bullish_signal(self) -> None:
        plugin = WilliamsStrategy(risk_reward_ratio=2.0)
        df = _make_bullish_df()
        result = await plugin.evaluate("BTCUSDT", "15m", df)
        assert isinstance(result, SignalResult), (
            f"Expected SignalResult, got {type(result)}: {result}"
        )
        assert result.direction == "LONG"
        assert result.entry_price > 0
        assert result.stop_loss > 0
        assert result.take_profit > 0
        assert result.take_profit > result.entry_price

    async def test_bearish_signal(self) -> None:
        plugin = WilliamsStrategy(risk_reward_ratio=2.0)
        df = _make_bearish_df()
        result = await plugin.evaluate("ETHUSDT", "15m", df)
        assert isinstance(result, SignalResult), (
            f"Expected SignalResult, got {type(result)}: {result}"
        )
        assert result.direction == "SHORT"
        assert result.take_profit < result.entry_price

    async def test_no_signal(self) -> None:
        plugin = WilliamsStrategy()
        df = _make_no_signal_df()
        result = await plugin.evaluate("SOLUSDT", "15m", df)
        assert isinstance(result, NullSignalResult), (
            f"Expected NullSignalResult, got {type(result)}: {result}"
        )
        assert result.reason == "conditions_not_met"


# ─── TEST_033_08: Fractal caching ──────────────────────────────────────────────


class TestFractalCaching:
    async def test_fractal_functions_called_once(self) -> None:
        """last_valid_fractal_high e last_valid_fractal_low são chamados no max 1× cada."""
        import src.strategy.indicators as ind_mod

        orig_high = ind_mod.last_valid_fractal_high
        orig_low = ind_mod.last_valid_fractal_low

        call_count_high = 0
        call_count_low = 0

        def counting_high(*args, **kwargs):
            nonlocal call_count_high
            call_count_high += 1
            return orig_high(*args, **kwargs)

        def counting_low(*args, **kwargs):
            nonlocal call_count_low
            call_count_low += 1
            return orig_low(*args, **kwargs)

        ind_mod.last_valid_fractal_high = counting_high
        ind_mod.last_valid_fractal_low = counting_low

        try:
            plugin = WilliamsStrategy()
            df = _make_bullish_df()
            await plugin.evaluate("BTCUSDT", "15m", df)

            assert call_count_high <= 1, (
                f"last_valid_fractal_high called {call_count_high} times (expected <= 1)"
            )
            assert call_count_low <= 1, (
                f"last_valid_fractal_low called {call_count_low} times (expected <= 1)"
            )
        finally:
            ind_mod.last_valid_fractal_high = orig_high
            ind_mod.last_valid_fractal_low = orig_low


# ─── TEST_033_09: Confidence bounds ───────────────────────────────────────────


class TestConfidenceBounds:
    async def test_confidence_in_range(self) -> None:
        plugin = WilliamsStrategy()
        df = _make_bullish_df()
        conditions = plugin._check_conditions("BTCUSDT", "15m", df)
        assert conditions is not None, "Bullish DataFrame should produce conditions"
        confidence = plugin._calculate_confidence(conditions, df)
        assert 0.0 <= confidence <= 1.0, f"Confidence {confidence} out of [0, 1]"

    async def test_confidence_high_for_strong_signal(self) -> None:
        """Alligator bullish + AO forte + fractal próximo → confidence > 0.3."""
        plugin = WilliamsStrategy()
        df = _make_bullish_df()
        # Reforçar sinal: AO grande, ATR pequeno, fractal logo abaixo do close
        df["ao"] = 5.0
        df["atr"] = 0.5
        df.loc[df.index[-3], "fractal_high"] = (
            df["close"].iloc[-1] * 0.999
        )  # fractal logo abaixo do close

        conditions = plugin._check_conditions("BTCUSDT", "15m", df)
        assert conditions is not None
        confidence = plugin._calculate_confidence(conditions, df)
        assert 0.0 <= confidence <= 1.0, f"Confidence {confidence} out of bounds"
        assert confidence >= 0.3, f"Strong signal should have high confidence, got {confidence}"


# ─── TEST_033_10: TimeoutDecorator ────────────────────────────────────────────


class TestTimeoutDecorator:
    async def test_slow_plugin_returns_null_signal_result(self) -> None:
        """Plugin que excede o timeout retorna NullSignalResult."""

        class _SlowPlugin(WilliamsStrategy):
            async def evaluate(
                self, symbol: str, timeframe: str, df: pd.DataFrame
            ) -> SignalResult | NullSignalResult:
                await asyncio.sleep(5)  # simula latência
                return await super().evaluate(symbol, timeframe, df)

        plugin = _SlowPlugin()
        decorator = TimeoutDecorator(plugin, timeout=0.1)  # 100ms timeout
        df = _make_bullish_df()
        result = await decorator.evaluate("BTCUSDT", "15m", df)
        assert isinstance(result, NullSignalResult)
        assert result.reason == "timeout"

    async def test_fast_plugin_passes_through(self) -> None:
        """Plugin rápido retorna resultado normal mesmo com timeout."""
        plugin = WilliamsStrategy()
        decorator = TimeoutDecorator(plugin, timeout=5.0)
        df = _make_bullish_df()
        result = await decorator.evaluate("BTCUSDT", "15m", df)
        assert isinstance(result, SignalResult)


# ─── TEST_033_11: ValidationDecorator ─────────────────────────────────────────


class TestValidationDecorator:
    async def test_invalid_sl_returns_null(self) -> None:
        """stop_loss <= 0 → NullSignalResult."""

        class _BadSlPlugin(WilliamsStrategy):
            def _check_conditions(
                self, symbol: str, timeframe: str, df: pd.DataFrame
            ) -> dict | None:
                return {"direction": "LONG", "entry_price": 100, "stop_loss": 0, "metadata": {}}

            def _calculate_targets(self, conditions: dict, df: pd.DataFrame) -> dict:
                return {"entry_price": 100, "stop_loss": 0, "take_profit": 120}

        plugin = _BadSlPlugin()
        decorator = ValidationDecorator(plugin)
        df = _make_bullish_df()
        result = await decorator.evaluate("BTCUSDT", "15m", df)
        assert isinstance(result, NullSignalResult)
        assert result.reason == "invalid_sl_tp_bounds"

    async def test_invalid_tp_returns_null(self) -> None:
        """take_profit <= 0 → NullSignalResult."""

        class _BadTpPlugin(WilliamsStrategy):
            def _check_conditions(
                self, symbol: str, timeframe: str, df: pd.DataFrame
            ) -> dict | None:
                return {"direction": "LONG", "entry_price": 100, "stop_loss": 95, "metadata": {}}

            def _calculate_targets(self, conditions: dict, df: pd.DataFrame) -> dict:
                return {"entry_price": 100, "stop_loss": 95, "take_profit": -1}

        plugin = _BadTpPlugin()
        decorator = ValidationDecorator(plugin)
        df = _make_bullish_df()
        result = await decorator.evaluate("BTCUSDT", "15m", df)
        assert isinstance(result, NullSignalResult)
        assert result.reason == "invalid_sl_tp_bounds"

    async def test_invalid_entry_price_returns_null(self) -> None:
        """entry_price <= 0 → NullSignalResult."""

        class _BadEntryPlugin(WilliamsStrategy):
            def _check_conditions(
                self, symbol: str, timeframe: str, df: pd.DataFrame
            ) -> dict | None:
                return {"direction": "LONG", "entry_price": 0, "stop_loss": 95, "metadata": {}}

            def _calculate_targets(self, conditions: dict, df: pd.DataFrame) -> dict:
                return {"entry_price": 0, "stop_loss": 95, "take_profit": 120}

        plugin = _BadEntryPlugin()
        decorator = ValidationDecorator(plugin)
        df = _make_bullish_df()
        result = await decorator.evaluate("BTCUSDT", "15m", df)
        assert isinstance(result, NullSignalResult)
        assert result.reason == "invalid_entry_price"

    async def test_valid_result_passes_through(self) -> None:
        """SignalResult válido passa pelo ValidationDecorator sem alteração."""
        plugin = WilliamsStrategy()
        decorator = ValidationDecorator(plugin)
        df = _make_bullish_df()
        result = await decorator.evaluate("BTCUSDT", "15m", df)
        assert isinstance(result, SignalResult)


# ─── TEST_033_12: MetricsDecorator ────────────────────────────────────────────


class TestMetricsDecorator:
    async def test_metrics_called_for_signal_result(self) -> None:
        """SignalResult → record_signal_evaluated + record_signal_detected chamados."""
        plugin = WilliamsStrategy()
        decorator = MetricsDecorator(plugin)

        with (
            patch("src.strategy.plugin_decorator.record_signal_evaluated") as mock_eval,
            patch("src.strategy.plugin_decorator.record_signal_detected") as mock_detect,
        ):
            df = _make_bullish_df()
            result = await decorator.evaluate("BTCUSDT", "15m", df)

        assert isinstance(result, SignalResult), "Bullish df should produce signal"
        mock_eval.assert_called_once_with("BTCUSDT", "15m")
        mock_detect.assert_called_once()
        args, _ = mock_detect.call_args
        assert args[0] == "BTCUSDT"
        assert args[1] == "15m"
        assert args[2] == "long"

    async def test_metrics_not_called_for_null_result(self) -> None:
        """NullSignalResult → record_signal_evaluated chamado, record_signal_detected NÃO."""
        plugin = WilliamsStrategy()
        decorator = MetricsDecorator(plugin)

        with (
            patch("src.strategy.plugin_decorator.record_signal_evaluated") as mock_eval,
            patch("src.strategy.plugin_decorator.record_signal_detected") as mock_detect,
        ):
            df = _make_no_signal_df()
            result = await decorator.evaluate("BTCUSDT", "15m", df)

        assert isinstance(result, NullSignalResult)
        mock_eval.assert_called_once_with("BTCUSDT", "15m")
        mock_detect.assert_not_called()
