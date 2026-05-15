"""
WilliamsStrategy — Plugin concreto da estratégia BO Williams.

Implementa o Template Method definido em StrategyPlugin com os três
pilares: Alligator (SMMA), Awesome Oscillator, e Fractais de 5 barras.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from src.monitoring.logger import get_logger
from src.strategy.indicators import (
    _count_recent_crosses,
    compute_all_optimized,
)
from src.strategy.plugin_base import StrategyPlugin
from src.strategy.signal_engine import is_alligator_bearish, is_alligator_bullish

logger = get_logger(__name__)


@dataclass(frozen=True)
class _EvaluationContext:
    close: float
    jaw: float
    teeth: float
    lips: float
    ao: float
    fractal_high: float | None
    fractal_low: float | None


@dataclass(frozen=True)
class _DirectionParams:
    direction: str
    event_name: str
    alligator_check: Callable[[float, float, float, float], bool]
    ao_check: Callable[[float], bool]
    breakout_fractal_getter: Callable[[_EvaluationContext], float | None]
    breakout_check: Callable[[float, float], bool]
    stop_fractal_getter: Callable[[_EvaluationContext], float | None]
    stop_valid_check: Callable[[float, float], bool]


def _is_ao_positive(ao: float) -> bool:
    return ao > 0


def _is_ao_negative(ao: float) -> bool:
    return ao < 0


def _get_fractal_high(context: _EvaluationContext) -> float | None:
    return context.fractal_high


def _get_fractal_low(context: _EvaluationContext) -> float | None:
    return context.fractal_low


def _breakout_above(close: float, fractal: float) -> bool:
    return close > fractal


def _breakout_below(close: float, fractal: float) -> bool:
    return close < fractal


def _stop_below(close: float, stop: float) -> bool:
    return stop < close


def _stop_above(close: float, stop: float) -> bool:
    return stop > close


_DIRECTION_PARAMS: tuple[_DirectionParams, ...] = (
    _DirectionParams(
        direction="LONG",
        event_name="long_conditions_check",
        alligator_check=is_alligator_bullish,
        ao_check=_is_ao_positive,
        breakout_fractal_getter=_get_fractal_high,
        breakout_check=_breakout_above,
        stop_fractal_getter=_get_fractal_low,
        stop_valid_check=_stop_below,
    ),
    _DirectionParams(
        direction="SHORT",
        event_name="short_conditions_check",
        alligator_check=is_alligator_bearish,
        ao_check=_is_ao_negative,
        breakout_fractal_getter=_get_fractal_low,
        breakout_check=_breakout_below,
        stop_fractal_getter=_get_fractal_high,
        stop_valid_check=_stop_above,
    ),
)


def calculate_targets(
    direction: str,
    entry_price: float,
    stop_loss: float,
    risk_reward_ratio: float,
) -> dict:
    if direction == "LONG":
        take_profit = entry_price + (entry_price - stop_loss) * risk_reward_ratio
    elif direction == "SHORT":
        take_profit = entry_price - (stop_loss - entry_price) * risk_reward_ratio
    else:
        raise ValueError(f"Direção inválida: {direction!r}")
    return {
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
    }


class WilliamsStrategy(StrategyPlugin):
    def __init__(self, risk_reward_ratio: float = 2.0) -> None:
        super().__init__(risk_reward_ratio)
        self._plugin_name = "williams"

    def warmup_candles(self) -> int:
        return 34

    def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        required_cols = {"jaw", "teeth", "lips", "ao"}
        if required_cols.issubset(df.columns):
            return df
        return compute_all_optimized(df)

    def _check_conditions(self, symbol: str, timeframe: str, df: pd.DataFrame) -> dict | None:
        last = df.iloc[-1]
        fractal_window = df[["fractal_high", "fractal_low"]].iloc[-102:-2]
        context = _EvaluationContext(
            close=float(last["close"]),
            jaw=float(last["jaw"]),
            teeth=float(last["teeth"]),
            lips=float(last["lips"]),
            ao=float(last["ao"]),
            fractal_high=self._last_valid_fractal_value(fractal_window["fractal_high"]),
            fractal_low=self._last_valid_fractal_value(fractal_window["fractal_low"]),
        )

        logger.debug(
            "williams_check",
            symbol=symbol,
            close=context.close,
            jaw=context.jaw,
            teeth=context.teeth,
            lips=context.lips,
            ao=context.ao,
            fractal_high=context.fractal_high,
            fractal_low=context.fractal_low,
        )

        for params in self._direction_params():
            signal = self._evaluate_direction(symbol, timeframe, context, params)
            if signal is not None:
                return signal

        return None

    def _direction_params(self) -> tuple[_DirectionParams, ...]:
        return _DIRECTION_PARAMS

    def _evaluate_direction(
        self,
        symbol: str,
        timeframe: str,
        context: _EvaluationContext,
        params: _DirectionParams,
    ) -> dict | None:
        alligator_ok = params.alligator_check(
            context.jaw, context.teeth, context.lips, context.close
        )
        ao_ok = params.ao_check(context.ao)
        breakout_ref = params.breakout_fractal_getter(context)
        breakout_ok = breakout_ref is not None and params.breakout_check(
            context.close, breakout_ref
        )
        stop_ref = params.stop_fractal_getter(context)
        stop_ok = stop_ref is not None and params.stop_valid_check(context.close, stop_ref)

        logger.debug(
            params.event_name,
            symbol=symbol,
            timeframe=timeframe,
            direction=params.direction,
            close=context.close,
            jaw=context.jaw,
            teeth=context.teeth,
            lips=context.lips,
            ao=context.ao,
            breakout_ref=breakout_ref,
            stop_ref=stop_ref,
            alligator_ok=alligator_ok,
            ao_ok=ao_ok,
            breakout_ok=breakout_ok,
            stop_ok=stop_ok,
        )

        if not (alligator_ok and ao_ok and breakout_ok and stop_ok):
            return None

        entry_price = context.close
        stop_loss = stop_ref
        if stop_loss is None:
            return None

        return {
            "direction": params.direction,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "metadata": {
                "indicators": {
                    "alligator_jaws": {
                        "jaw": context.jaw,
                        "teeth": context.teeth,
                        "lips": context.lips,
                    },
                    "ao_value": context.ao,
                    "fractal_high": context.fractal_high,
                    "fractal_low": context.fractal_low,
                }
            },
        }

    @staticmethod
    def _last_valid_fractal_value(series: pd.Series) -> float | None:
        valid = series.dropna()
        return float(valid.iloc[-1]) if not valid.empty else None

    def _calculate_targets(self, conditions: dict, df: pd.DataFrame) -> dict:
        return calculate_targets(
            direction=conditions["direction"],
            entry_price=conditions["entry_price"],
            stop_loss=conditions["stop_loss"],
            risk_reward_ratio=self._rrr,
        )

    def _calculate_confidence(self, conditions: dict, df: pd.DataFrame) -> float:
        ao_value = abs(conditions.get("metadata", {}).get("indicators", {}).get("ao_value", 0))
        last_close = float(df["close"].iloc[-1])
        atr_value = float(df["atr"].iloc[-1]) if "atr" in df else 0.0

        ao_score = min(ao_value / (atr_value or 0.001), 0.5)
        cross_score = min(_count_recent_crosses(df) / 5.0, 0.3)
        fractal_dist = self._fractal_distance_score(conditions, last_close)
        confidence = ao_score + cross_score + fractal_dist
        return min(max(confidence, 0.0), 1.0)

    @staticmethod
    def _fractal_distance_score(conditions: dict, close: float) -> float:
        indicators = conditions.get("metadata", {}).get("indicators", {})
        fractal_high = indicators.get("fractal_high")
        fractal_low = indicators.get("fractal_low")
        if conditions["direction"] == "LONG" and fractal_high:
            return min(abs(close - fractal_high) / close, 0.2)
        elif conditions["direction"] == "SHORT" and fractal_low:
            return min(abs(close - fractal_low) / close, 0.2)
        return 0.0
