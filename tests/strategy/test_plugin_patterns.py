"""
Testes SPEC_033 — SignalEngine + Integration (TEST_033_13 a 16).

Verifica:
    - Chain of Responsibility (fallback + short-circuit)
    - symbol_strategy_map per-symbol
    - SignalEngine corpus compatibility
    - Observer Pattern (4 sub-tests)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pandas as pd

from src.strategies.williams_strategy import WilliamsStrategy
from src.strategy.plugin_base import NullSignalResult, SignalResult, StrategyPlugin
from src.strategy.plugin_registry import PluginRegistry
from src.strategy.signal_engine import SignalEngine, SignalEvent, SignalEventData

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_bullish_df(n: int = 50) -> pd.DataFrame:
    """DataFrame com alligator bullish e AO > 0."""
    np.random.seed(42)
    close = np.linspace(100, 110, n) + np.random.randn(n) * 0.5
    high = close + np.random.rand(n) * 2.0 + 1.0
    low = close - np.random.rand(n) * 2.0 - 1.0
    close[-3:] = [109.0, 109.5, 110.0]

    df = pd.DataFrame(
        {"open": close * 0.99, "high": high, "low": low, "close": close, "volume": 1000}
    )
    df["jaw"] = 104.0
    df["teeth"] = 105.0
    df["lips"] = 106.0
    df["ao"] = 2.5
    df["fractal_high"] = np.nan
    df["fractal_low"] = np.nan
    if len(df) >= 3:
        df.loc[df.index[-3], "fractal_high"] = 107.0
        df.loc[df.index[-4], "fractal_low"] = 103.0
    df["atr"] = 1.5
    return df


def _make_no_signal_df(n: int = 50) -> pd.DataFrame:
    """DataFrame sem sinal."""
    df = pd.DataFrame(
        {
            "open": [100.0] * n,
            "high": [102.0] * n,
            "low": [98.0] * n,
            "close": [100.0] * n,
            "volume": [1000] * n,
        }
    )
    df["jaw"] = 102.0
    df["teeth"] = 101.0
    df["lips"] = 100.0
    df["ao"] = 0.0
    df["fractal_high"] = np.nan
    df["fractal_low"] = np.nan
    if len(df) >= 3:
        df.loc[df.index[-3], "fractal_high"] = 103.0
        df.loc[df.index[-4], "fractal_low"] = 98.0
    df["atr"] = 1.0
    return df


class _EchoPlugin(StrategyPlugin):
    """Plugin que retorna SignalResult com direction fixa."""

    def __init__(self, name: str = "echo", direction: str = "LONG") -> None:
        super().__init__(risk_reward_ratio=2.0)
        self._plugin_name = name
        self._fixed_direction = direction

    def warmup_candles(self) -> int:
        return 10

    def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        return df

    def _check_conditions(self, symbol: str, timeframe: str, df: pd.DataFrame) -> dict | None:
        return {
            "direction": self._fixed_direction,
            "entry_price": 100,
            "stop_loss": 95,
            "metadata": {},
        }

    def _calculate_targets(self, conditions: dict, df: pd.DataFrame) -> dict:
        return {"entry_price": 100, "stop_loss": 95, "take_profit": 110}

    def _calculate_confidence(self, conditions: dict, df: pd.DataFrame) -> float:
        return 0.8


class _FailPlugin(StrategyPlugin):
    """Plugin que sempre retorna NullSignalResult."""

    def __init__(self, name: str = "fail") -> None:
        super().__init__(risk_reward_ratio=2.0)
        self._plugin_name = name

    def warmup_candles(self) -> int:
        return 10

    def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        return df

    def _check_conditions(self, symbol: str, timeframe: str, df: pd.DataFrame) -> dict | None:
        return None

    def _calculate_targets(self, conditions: dict, df: pd.DataFrame) -> dict:
        return {}

    def _calculate_confidence(self, conditions: dict, df: pd.DataFrame) -> float:
        return 0.0


# ─── TEST_033_13: Chain of Responsibility ─────────────────────────────────────


class TestChainOfResponsibility:
    async def test_fallback_to_williams(self) -> None:
        """Handle 1 (config) falha → chain cai no Handle 2 (williams)."""
        registry = PluginRegistry(plugin_timeout=30.0)
        registry.register("williams", WilliamsStrategy())
        registry.register("custom_fail", _FailPlugin(name="custom_fail"))
        engine = SignalEngine(
            plugin_registry=registry,
            default_strategy="custom_fail",
            symbol_strategy_map={"BTCUSDT": "custom_fail"},
        )
        df = _make_bullish_df()
        result_obj = await engine.evaluate("BTCUSDT", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()
        assert isinstance(result, SignalResult), (
            f"Expected SignalResult from williams fallback, got {type(result)}: {result}"
        )
        assert result.metadata is None or result.metadata.get("plugin") == "williams"

    async def test_short_circuit_on_first_hit(self) -> None:
        """Handle 1 retorna SignalResult → chain não continua para Handle 2."""
        registry = PluginRegistry(plugin_timeout=30.0)
        registry.register("williams", WilliamsStrategy())
        registry.register("echo_long", _EchoPlugin(name="echo_long", direction="LONG"))
        engine = SignalEngine(
            plugin_registry=registry,
            default_strategy="echo_long",
            symbol_strategy_map={"BTCUSDT": "echo_long"},
        )
        df = _make_bullish_df()
        result_obj = await engine.evaluate("BTCUSDT", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()
        assert isinstance(result, SignalResult)
        assert result.direction == "LONG"

    async def test_chain_returns_null_on_all_fail(self) -> None:
        """Todos os handles retornam NullSignalResult → engine retorna NullSignalResult."""
        registry = PluginRegistry(plugin_timeout=30.0)
        registry.register("williams", WilliamsStrategy())
        registry.register("always_fail", _FailPlugin(name="always_fail"))
        engine = SignalEngine(
            plugin_registry=registry,
            default_strategy="always_fail",
        )
        df = _make_no_signal_df()
        result_obj = await engine.evaluate("BTCUSDT", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()
        assert isinstance(result, NullSignalResult)
        assert result.reason != "no_plugin_matched", (
            "Chain should have handlers but all returned null"
        )


# ─── TEST_033_14: symbol_strategy_map ─────────────────────────────────────────


class TestSymbolStrategyMap:
    async def test_different_symbol_different_chain(self) -> None:
        """Símbolos diferentes resolvem para plugins diferentes na chain."""
        registry = PluginRegistry(plugin_timeout=30.0)
        registry.register("williams", WilliamsStrategy())
        registry.register("echo_short", _EchoPlugin(name="echo_short", direction="SHORT"))
        engine = SignalEngine(
            plugin_registry=registry,
            default_strategy="echo_short",
            symbol_strategy_map={"BTCUSDT": "williams"},
        )

        # BTCUSDT → williams plugin only (early return because williams)
        df_btc = _make_bullish_df()
        result_btc_obj = await engine.evaluate("BTCUSDT", "15m", df_btc)
        assert result_btc_obj.is_ok()
        result_btc = result_btc_obj.unwrap()
        assert isinstance(result_btc, SignalResult)

        # ETHUSDT → echo_short (default_strategy)
        df_eth = _make_bullish_df()
        result_eth_obj = await engine.evaluate("ETHUSDT", "15m", df_eth)
        assert result_eth_obj.is_ok()
        result_eth = result_eth_obj.unwrap()
        assert isinstance(result_eth, SignalResult)
        # Verifica que o direction é do echo_short
        assert result_eth.direction == "SHORT"

    async def test_unmapped_symbol_uses_default(self) -> None:
        """Símbolo não mapeado usa default_strategy."""
        registry = PluginRegistry(plugin_timeout=30.0)
        registry.register("williams", WilliamsStrategy())
        registry.register("echo_long", _EchoPlugin(name="echo_long"))
        engine = SignalEngine(
            plugin_registry=registry,
            default_strategy="echo_long",
        )
        df = _make_bullish_df()
        result_obj = await engine.evaluate("UNKNOWN", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()
        assert isinstance(result, SignalResult)
        assert result.direction == "LONG"  # echo_long retorna LONG


# ─── TEST_033_15: Corpus compatibility ────────────────────────────────────────


class TestCorpusCompatibility:
    async def test_insufficient_candles_returns_null(self) -> None:
        """DataFrame com < 50 candles retorna NullSignalResult."""
        registry = PluginRegistry(plugin_timeout=30.0)
        registry.register("williams", WilliamsStrategy())
        engine = SignalEngine(plugin_registry=registry)
        df = pd.DataFrame({"close": [100.0] * 10})
        result_obj = await engine.evaluate("BTCUSDT", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()
        assert isinstance(result, NullSignalResult)
        assert result.reason == "insufficient_candles"

    async def test_missing_indicators_returns_null(self) -> None:
        """DataFrame sem colunas de indicadores retorna NullSignalResult."""
        registry = PluginRegistry(plugin_timeout=30.0)
        registry.register("williams", WilliamsStrategy())
        engine = SignalEngine(plugin_registry=registry)
        df = pd.DataFrame({"close": [100.0] * 60})
        result_obj = await engine.evaluate("BTCUSDT", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()
        assert isinstance(result, NullSignalResult)
        assert result.reason == "indicators_not_enriched"

    async def test_no_registry_returns_null(self) -> None:
        """SignalEngine sem registry retorna NullSignalResult."""
        engine = SignalEngine()
        df = _make_bullish_df()
        result_obj = await engine.evaluate("BTCUSDT", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()
        assert isinstance(result, NullSignalResult)

    async def test_corpus_like_data_returns_signal(self) -> None:
        """Dados que se parecem com corpus bullish produzem SignalResult."""
        registry = PluginRegistry(plugin_timeout=30.0)
        registry.register("williams", WilliamsStrategy())
        engine = SignalEngine(plugin_registry=registry)
        df = _make_bullish_df()
        result_obj = await engine.evaluate("BTCUSDT", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()
        assert isinstance(result, SignalResult)
        assert result.direction in ("LONG", "SHORT")


# ─── TEST_033_16: Observer Pattern ────────────────────────────────────────────


class TestObserverPattern:
    async def test_detected_event_emitted(self) -> None:
        """SignalResult → evento DETECTED emitido."""
        registry = PluginRegistry(plugin_timeout=30.0)
        registry.register("williams", WilliamsStrategy())
        engine = SignalEngine(plugin_registry=registry)

        callback = MagicMock()
        engine.on(SignalEvent.DETECTED, callback)

        df = _make_bullish_df()
        result_obj = await engine.evaluate("BTCUSDT", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()

        assert isinstance(result, SignalResult)
        callback.assert_called_once()
        call_data = callback.call_args[0][0]
        assert isinstance(call_data, SignalEventData)
        assert call_data.event == SignalEvent.DETECTED
        assert call_data.symbol == "BTCUSDT"
        assert call_data.timeframe == "15m"
        assert call_data.result is result

    async def test_rejected_event_emitted_on_insufficient_candles(self) -> None:
        """DataFrame pequeno → evento REJECTED emitido."""
        engine = SignalEngine()
        callback = MagicMock()
        engine.on(SignalEvent.REJECTED, callback)

        df = pd.DataFrame({"close": [100.0] * 10})
        result_obj = await engine.evaluate("BTCUSDT", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()

        assert isinstance(result, NullSignalResult)
        callback.assert_called_once()
        call_data = callback.call_args[0][0]
        assert call_data.event == SignalEvent.REJECTED
        assert call_data.symbol == "BTCUSDT"
        assert call_data.result is result

    async def test_evaluated_event_emitted_when_no_signal(self) -> None:
        """NullSignalResult sem rejection → evento EVALUATED emitido."""
        registry = PluginRegistry(plugin_timeout=30.0)
        registry.register("williams", WilliamsStrategy())
        registry.register("always_fail", _FailPlugin(name="always_fail"))
        engine = SignalEngine(plugin_registry=registry, default_strategy="always_fail")

        callback = MagicMock()
        engine.on(SignalEvent.EVALUATED, callback)

        df = _make_no_signal_df()
        result_obj = await engine.evaluate("BTCUSDT", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()

        assert isinstance(result, NullSignalResult)
        callback.assert_called_once()
        call_data = callback.call_args[0][0]
        assert call_data.event == SignalEvent.EVALUATED
        assert call_data.symbol == "BTCUSDT"
        assert call_data.result is result

    async def test_observer_exception_does_not_break_evaluate(self) -> None:
        """Exceção em callback não quebra evaluate() — retorna resultado normal."""
        registry = PluginRegistry(plugin_timeout=30.0)
        registry.register("williams", WilliamsStrategy())
        engine = SignalEngine(plugin_registry=registry)

        def _broken_callback(data: SignalEventData) -> None:
            raise RuntimeError("observer crashed")

        engine.on(SignalEvent.DETECTED, _broken_callback)
        engine.on(SignalEvent.EVALUATED, _broken_callback)
        engine.on(SignalEvent.REJECTED, _broken_callback)

        df = _make_bullish_df()
        result_obj = await engine.evaluate("BTCUSDT", "15m", df)
        assert result_obj.is_ok()
        result = result_obj.unwrap()

        # Apesar de todos os observers terem lançado exceção, o resultado
        # deve ser o SignalResult normal (não NullSignalResult)
        assert isinstance(result, SignalResult), (
            f"Expected SignalResult despite broken observer, got {type(result)}"
        )
