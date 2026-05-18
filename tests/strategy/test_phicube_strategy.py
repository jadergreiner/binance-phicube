from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.phicube_strategy import PhicubeStrategy
from src.strategy.plugin_base import NullSignalResult, SignalResult


def _base_df(n: int = 60) -> pd.DataFrame:
    close = np.linspace(100, 105, n)
    high = close + 1.5
    low = close - 1.5
    df = pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": 1000})
    df["fractal_high"] = np.nan
    df["fractal_low"] = np.nan
    df["atr"] = 1.0
    return df


def _bullish_df() -> pd.DataFrame:
    df = _base_df()
    n = len(df)
    df["jaw"] = np.linspace(100.0, 101.5, n)
    df["teeth"] = np.linspace(101.0, 102.5, n)
    df["lips"] = np.linspace(102.0, 103.5, n)
    df["ao"] = np.linspace(0.2, 0.8, n)
    df.loc[df.index[-5], "fractal_low"] = float(df["close"].iloc[-1] - 2.5)
    df.loc[df.index[-6], "fractal_high"] = float(df["close"].iloc[-1] - 0.4)
    return df


def _bearish_df() -> pd.DataFrame:
    n = 60
    close = np.linspace(105, 100, n)
    high = close + 1.5
    low = close - 1.5
    df = pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": 1000})
    df["fractal_high"] = np.nan
    df["fractal_low"] = np.nan
    df["atr"] = 1.0
    df["jaw"] = np.linspace(104.0, 103.0, n)
    df["teeth"] = np.linspace(103.0, 102.0, n)
    df["lips"] = np.linspace(102.0, 101.0, n)
    df["ao"] = np.linspace(-0.2, -0.8, n)
    df.loc[df.index[-5], "fractal_high"] = float(df["close"].iloc[-1] + 2.5)
    df.loc[df.index[-6], "fractal_low"] = float(df["close"].iloc[-1] + 0.4)
    return df


def _consolidation_df() -> pd.DataFrame:
    df = _base_df()
    n = len(df)
    df["jaw"] = np.linspace(101.0, 101.0, n)
    df["teeth"] = np.linspace(101.0, 101.2, n)
    df["lips"] = np.linspace(101.5, 101.3, n)
    df["ao"] = np.linspace(0.1, -0.1, n)
    df.loc[df.index[-5], "fractal_high"] = float(df["close"].iloc[-1] + 2.0)
    df.loc[df.index[-6], "fractal_low"] = float(df["close"].iloc[-1] - 2.0)
    return df


async def test_phicube_returns_long_signal_with_rule_hits() -> None:
    plugin = PhicubeStrategy(risk_reward_ratio=2.0)
    result = await plugin.evaluate("ADAUSDT", "15m", _bullish_df())
    assert isinstance(result, SignalResult)
    assert result.direction == "LONG"
    assert result.metadata is not None
    hits = result.metadata.get("rule_hits", [])
    assert any("RN-PHI-015:long_setup_valid" in hit for hit in hits)
    assert any("RN-PHI-024:chart_confirmed" in hit for hit in hits)
    assert result.metadata.get("reason") == "long_setup_valid"
    assert result.metadata.get("market_state") == "strong_up"


async def test_phicube_returns_short_signal_with_rule_hits() -> None:
    plugin = PhicubeStrategy(risk_reward_ratio=2.0)
    result = await plugin.evaluate("ADAUSDT", "15m", _bearish_df())
    assert isinstance(result, SignalResult)
    assert result.direction == "SHORT"
    assert result.metadata is not None
    hits = result.metadata.get("rule_hits", [])
    assert any("RN-PHI-016:short_setup_valid" in hit for hit in hits)
    assert any("RN-PHI-024:chart_confirmed" in hit for hit in hits)
    assert result.metadata.get("reason") == "short_setup_valid"
    assert result.metadata.get("market_state") == "strong_down"


async def test_phicube_returns_no_setup_in_consolidation() -> None:
    plugin = PhicubeStrategy()
    result = await plugin.evaluate("ADAUSDT", "15m", _consolidation_df())
    assert isinstance(result, NullSignalResult)
    assert result.reason in {"conditions_not_met", "no_setup_detected"}
    assert result.metadata is not None
    hits = result.metadata.get("rule_hits", [])
    assert any("RN-PHI-005" in hit for hit in hits)
    assert result.metadata.get("market_state") == "consolidation"
    assert result.metadata.get("reason") == "no_setup_detected"


async def test_phicube_returns_insufficient_data_when_less_than_warmup() -> None:
    plugin = PhicubeStrategy()
    result = await plugin.evaluate("ADAUSDT", "15m", _base_df(n=20))
    assert isinstance(result, NullSignalResult)
    assert result.reason == "insufficient_data"
    assert result.metadata is not None
    assert result.metadata.get("plugin") == "phicube"


def _transition_df() -> pd.DataFrame:
    df = _base_df()
    n = len(df)
    df["jaw"] = np.linspace(101.0, 100.7, n)
    df["teeth"] = np.linspace(100.5, 100.8, n)
    df["lips"] = np.linspace(100.0, 100.4, n)
    df["ao"] = np.linspace(0.2, -0.2, n)
    df.loc[df.index[-5], "fractal_high"] = float(df["close"].iloc[-1] + 1.0)
    df.loc[df.index[-6], "fractal_low"] = float(df["close"].iloc[-1] - 1.0)
    return df


async def test_phicube_returns_transition_market_state_when_fractals_do_not_align() -> None:
    plugin = PhicubeStrategy()
    result = await plugin.evaluate("ADAUSDT", "15m", _transition_df())
    assert isinstance(result, NullSignalResult)
    assert result.metadata is not None
    assert result.metadata.get("market_state") == "transition"
    hits = result.metadata.get("rule_hits", [])
    assert any("RN-PHI-005:transition" in hit for hit in hits)


async def test_phicube_no_setup_keeps_chart_confirmation_and_gate_reason() -> None:
    plugin = PhicubeStrategy()
    result = await plugin.evaluate("ADAUSDT", "15m", _consolidation_df())
    assert isinstance(result, NullSignalResult)
    assert result.reason == "conditions_not_met"
    assert result.metadata is not None
    assert result.metadata.get("chart_confirmation") is True
    assert result.metadata.get("reason") == "no_setup_detected"
    hits = result.metadata.get("rule_hits", [])
    assert any("RN-PHI-013:proxy_fractal_support_resistance" in hit for hit in hits)
    assert any("RN-PHI-024:chart_confirmed" in hit for hit in hits)
