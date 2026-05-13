"""
WilliamsStrategy — Plugin concreto da estratégia BO Williams.

Implementa o Template Method definido em StrategyPlugin com os três
pilares: Alligator (SMMA), Awesome Oscillator, e Fractais de 5 barras.
"""

from __future__ import annotations

import pandas as pd

from src.monitoring.logger import get_logger
from src.strategy.indicators import (
    _count_recent_crosses,
    compute_all_optimized,
    last_valid_fractal_high,
    last_valid_fractal_low,
)
from src.strategy.plugin_base import StrategyPlugin
from src.strategy.signal_engine import is_alligator_bearish, is_alligator_bullish

logger = get_logger(__name__)


def calculate_targets(
    direction: str,
    entry_price: float,
    stop_loss: float,
    risk_reward_ratio: float,
) -> dict:
    if direction == "LONG":
        take_profit = entry_price + (entry_price - stop_loss) * risk_reward_ratio
    else:
        take_profit = entry_price - (stop_loss - entry_price) * risk_reward_ratio
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
        close = float(last["close"])
        jaw = float(last["jaw"])
        teeth = float(last["teeth"])
        lips = float(last["lips"])
        ao = float(last["ao"])

        fractal_high_val = last_valid_fractal_high(df)
        fractal_low_val = last_valid_fractal_low(df)

        logger.debug(
            "williams_check",
            symbol=symbol,
            close=close,
            jaw=jaw,
            teeth=teeth,
            lips=lips,
            ao=ao,
            fractal_high=fractal_high_val,
            fractal_low=fractal_low_val,
        )

        alligator_bullish = is_alligator_bullish(jaw, teeth, lips, close)
        alligator_bearish = is_alligator_bearish(jaw, teeth, lips, close)

        if (
            alligator_bullish
            and ao > 0
            and fractal_high_val is not None
            and close > fractal_high_val
            and fractal_low_val is not None
            and fractal_low_val < close
        ):
            return {
                "direction": "LONG",
                "entry_price": close,
                "stop_loss": fractal_low_val,
                "metadata": {
                    "indicators": {
                        "alligator_jaws": {"jaw": jaw, "teeth": teeth, "lips": lips},
                        "ao_value": ao,
                        "fractal_high": fractal_high_val,
                        "fractal_low": fractal_low_val,
                    }
                },
            }

        if (
            alligator_bearish
            and ao < 0
            and fractal_low_val is not None
            and close < fractal_low_val
            and fractal_high_val is not None
            and fractal_high_val > close
        ):
            return {
                "direction": "SHORT",
                "entry_price": close,
                "stop_loss": fractal_high_val,
                "metadata": {
                    "indicators": {
                        "alligator_jaws": {"jaw": jaw, "teeth": teeth, "lips": lips},
                        "ao_value": ao,
                        "fractal_high": fractal_high_val,
                        "fractal_low": fractal_low_val,
                    }
                },
            }

        return None

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
