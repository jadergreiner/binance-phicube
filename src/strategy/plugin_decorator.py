"""
Plugin Decorator — cadeia GoF class-decorators para plugins de estratégia.

Ordem de empacotamento (de dentro para fora):
    MetricsDecorator → ValidationDecorator → TimeoutDecorator

Timeout é o mais externo para cobrir validação e métricas.
"""

from __future__ import annotations

import asyncio

import pandas as pd

from src.monitoring.metrics import record_signal_detected, record_signal_evaluated
from src.strategy.plugin_base import NullSignalResult, SignalResult, StrategyPlugin


class PluginDecorator(StrategyPlugin):
    def __init__(self, wrapped: StrategyPlugin) -> None:
        super().__init__(risk_reward_ratio=wrapped.risk_reward_ratio)
        self._wrapped = wrapped

    def warmup_candles(self) -> int:
        return self._wrapped.warmup_candles()

    @property
    def name(self) -> str:
        return self.wrapped_plugin.name

    def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._wrapped._compute_indicators(df)

    def _check_conditions(self, symbol: str, timeframe: str, df: pd.DataFrame) -> dict | None:
        return self._wrapped._check_conditions(symbol, timeframe, df)

    def _calculate_targets(self, conditions: dict, df: pd.DataFrame) -> dict:
        return self._wrapped._calculate_targets(conditions, df)

    def _calculate_confidence(self, conditions: dict, df: pd.DataFrame) -> float:
        return self._wrapped._calculate_confidence(conditions, df)

    @property
    def wrapped_plugin(self) -> StrategyPlugin:
        inner = self._wrapped
        while isinstance(inner, PluginDecorator):
            inner = inner._wrapped
        return inner

    def properties(self) -> dict:
        return {
            "decorator": type(self).__name__,
            "plugin": self._wrapped.name,
        }


class MetricsDecorator(PluginDecorator):
    async def evaluate(
        self, symbol: str, timeframe: str, df: pd.DataFrame
    ) -> SignalResult | NullSignalResult:
        record_signal_evaluated(symbol, timeframe)
        result = await self._wrapped.evaluate(symbol, timeframe, df)
        if result and isinstance(result, SignalResult):
            record_signal_detected(
                symbol,
                timeframe,
                result.direction.lower(),  # type: ignore[arg-type]
            )
        return result


class ValidationDecorator(PluginDecorator):
    async def evaluate(
        self, symbol: str, timeframe: str, df: pd.DataFrame
    ) -> SignalResult | NullSignalResult:
        result = await self._wrapped.evaluate(symbol, timeframe, df)
        if isinstance(result, SignalResult):
            if result.stop_loss <= 0 or result.take_profit <= 0:
                return NullSignalResult(reason="invalid_sl_tp_bounds")
            if result.entry_price <= 0:
                return NullSignalResult(reason="invalid_entry_price")
        return result


class TimeoutDecorator(PluginDecorator):
    def __init__(self, wrapped: StrategyPlugin, timeout: float = 30.0) -> None:
        super().__init__(wrapped)
        self._timeout = timeout

    async def evaluate(
        self, symbol: str, timeframe: str, df: pd.DataFrame
    ) -> SignalResult | NullSignalResult:
        try:
            result = await asyncio.wait_for(
                self._wrapped.evaluate(symbol, timeframe, df),
                timeout=self._timeout,
            )
        except TimeoutError:
            return NullSignalResult(reason="timeout")
        return result
