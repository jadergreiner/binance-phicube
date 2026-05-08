"""
Motor de detecção de sinais — Estratégia BO Williams (Phicube).

Regras de entrada (Long / Short) baseadas nos três pilares da estratégia:
    1. Alligator — determina a direção e se o mercado está "acordado"
    2. Awesome Oscillator (AO) — confirma o momentum
    3. Fractais — define o ponto de rompimento e o nível de stop

Regra Long (compra):
    - Alligator bullish: lips > teeth > jaw
    - Alligator "acordado": preço de fechamento acima das três linhas
    - AO positivo (acima de zero) na candle confirmada
    - Preço de fechamento rompe acima do último fractal de resistência (fractal_high)

Regra Short (venda):
    - Alligator bearish: lips < teeth < jaw
    - Alligator "acordado": preço de fechamento abaixo das três linhas
    - AO negativo (abaixo de zero) na candle confirmada
    - Preço de fechamento rompe abaixo do último fractal de suporte (fractal_low)

Stop Loss:
    - Long: fractal_low imediatamente anterior à entrada (suporte mais recente)
    - Short: fractal_high imediatamente anterior à entrada (resistência mais recente)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

import pandas as pd

from src.monitoring.logger import get_logger
from src.strategy.indicators import (
    compute_all,
    last_valid_fractal_high,
    last_valid_fractal_low,
)

logger = get_logger(__name__)


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True)
class Signal:
    symbol: str
    timeframe: str
    direction: Direction
    entry_price: float
    stop_loss: float
    take_profit: float
    fractal_ref: float
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def risk(self) -> float:
        return abs(self.entry_price - self.stop_loss)

    @property
    def reward(self) -> float:
        return abs(self.take_profit - self.entry_price)

    @property
    def risk_reward_ratio(self) -> float:
        if self.risk == 0:
            return 0.0
        return self.reward / self.risk

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "direction": self.direction.value,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "fractal_ref": self.fractal_ref,
            "risk": self.risk,
            "reward": self.reward,
            "risk_reward_ratio": self.risk_reward_ratio,
            "detected_at": self.detected_at,
        }


@dataclass(frozen=True)
class SignalEvaluation:
    symbol: str
    timeframe: str
    decision: str
    signal_generated: bool
    reason: str
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    candle_open_time: datetime | None = None
    long_conditions: dict[str, bool] | None = None
    short_conditions: dict[str, bool] | None = None

    def to_dict(self) -> dict:
        payload: dict[str, object] = {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "decision": self.decision,
            "signal_generated": self.signal_generated,
            "reason": self.reason,
            "evaluated_at": self.evaluated_at,
            "candle_open_time": self.candle_open_time,
            "long_conditions": self.long_conditions,
            "short_conditions": self.short_conditions,
        }
        return payload


class SignalEngine:
    """Evaluates a closed OHLCV DataFrame and returns a Signal or None."""

    def __init__(self, risk_reward_ratio: float = 2.0) -> None:
        self._rrr = risk_reward_ratio
        self._last_evaluation: SignalEvaluation | None = None

    def consume_last_evaluation(self) -> SignalEvaluation | None:
        evaluation = self._last_evaluation
        self._last_evaluation = None
        return evaluation

    def evaluate(
        self,
        symbol: str,
        timeframe: str,
        df: pd.DataFrame,
    ) -> Signal | None:
        """Evaluate the last *closed* candle for an entry signal.

        The caller must pass a DataFrame where the last row (index -1) is
        the most recent *closed* candle (i.e., not the live/building candle).
        Minimum required rows: 200 (for SMMA convergence).
        """
        if len(df) < 50:
            logger.debug("insufficient_candles", symbol=symbol, rows=len(df))
            self._last_evaluation = SignalEvaluation(
                symbol=symbol,
                timeframe=timeframe,
                decision="SKIPPED_INSUFFICIENT_CANDLES",
                signal_generated=False,
                reason="insufficient_candles",
            )
            return None

        enriched = compute_all(df)

        # Last closed candle
        last = enriched.iloc[-1]
        close = float(last["close"])

        jaw = last.get("jaw")
        teeth = last.get("teeth")
        lips = last.get("lips")
        ao = last.get("ao")

        if any(pd.isna(v) for v in [jaw, teeth, lips, ao]):
            logger.debug("indicators_not_ready", symbol=symbol)
            candle_open_time = last.get("open_time")
            self._last_evaluation = SignalEvaluation(
                symbol=symbol,
                timeframe=timeframe,
                decision="SKIPPED_INDICATORS_NOT_READY",
                signal_generated=False,
                reason="indicators_not_ready",
                candle_open_time=(
                    candle_open_time if isinstance(candle_open_time, datetime) else None
                ),
            )
            return None

        jaw, teeth, lips, ao = float(jaw), float(teeth), float(lips), float(ao)

        # ─── Long signal ──────────────────────────────────────────────────────
        alligator_bullish = self._is_alligator_bullish(jaw, teeth, lips, close)
        ao_positive = ao > 0
        fractal_high = last_valid_fractal_high(enriched)
        close_above_fractal = fractal_high is not None and close > fractal_high
        fractal_low = last_valid_fractal_low(enriched)
        valid_sl = fractal_low is not None and fractal_low < close

        logger.debug(
            "long_conditions_check",
            symbol=symbol,
            alligator_bullish=alligator_bullish,
            ao_positive=ao_positive,
            fractal_high=fractal_high,
            close_above_fractal=close_above_fractal,
            fractal_low=fractal_low,
            valid_sl=valid_sl,
        )

        if alligator_bullish and ao_positive and close_above_fractal and valid_sl:
            tp = close + (close - fractal_low) * self._rrr
            signal = Signal(
                symbol=symbol,
                timeframe=timeframe,
                direction=Direction.LONG,
                entry_price=close,
                stop_loss=fractal_low,
                take_profit=tp,
                fractal_ref=fractal_high,
            )
            logger.info("signal_detected", **signal.to_dict())
            self._last_evaluation = SignalEvaluation(
                symbol=symbol,
                timeframe=timeframe,
                decision="SIGNAL_LONG",
                signal_generated=True,
                reason="long_conditions_met",
                candle_open_time=last.get("open_time"),
                long_conditions={
                    "alligator_bullish": alligator_bullish,
                    "ao_positive": ao_positive,
                    "close_above_fractal": close_above_fractal,
                    "valid_sl": valid_sl,
                },
                short_conditions={
                    "alligator_bearish": False,
                    "ao_negative": False,
                    "close_below_fractal": False,
                    "valid_sl": False,
                },
            )
            return signal

        # ─── Short signal ─────────────────────────────────────────────────────
        alligator_bearish = self._is_alligator_bearish(jaw, teeth, lips, close)
        ao_negative = ao < 0
        fractal_low_ref = last_valid_fractal_low(enriched)
        close_below_fractal = fractal_low_ref is not None and close < fractal_low_ref
        fractal_high_ref = last_valid_fractal_high(enriched)
        valid_sl_short = fractal_high_ref is not None and fractal_high_ref > close

        logger.debug(
            "short_conditions_check",
            symbol=symbol,
            alligator_bearish=alligator_bearish,
            ao_negative=ao_negative,
            fractal_low=fractal_low_ref,
            close_below_fractal=close_below_fractal,
            fractal_high=fractal_high_ref,
            valid_sl=valid_sl_short,
        )

        if alligator_bearish and ao_negative and close_below_fractal and valid_sl_short:
            tp = close - (fractal_high_ref - close) * self._rrr
            signal = Signal(
                symbol=symbol,
                timeframe=timeframe,
                direction=Direction.SHORT,
                entry_price=close,
                stop_loss=fractal_high_ref,
                take_profit=tp,
                fractal_ref=fractal_low_ref,
            )
            logger.info("signal_detected", **signal.to_dict())
            self._last_evaluation = SignalEvaluation(
                symbol=symbol,
                timeframe=timeframe,
                decision="SIGNAL_SHORT",
                signal_generated=True,
                reason="short_conditions_met",
                candle_open_time=last.get("open_time"),
                long_conditions={
                    "alligator_bullish": alligator_bullish,
                    "ao_positive": ao_positive,
                    "close_above_fractal": close_above_fractal,
                    "valid_sl": valid_sl,
                },
                short_conditions={
                    "alligator_bearish": alligator_bearish,
                    "ao_negative": ao_negative,
                    "close_below_fractal": close_below_fractal,
                    "valid_sl": valid_sl_short,
                },
            )
            return signal

        long_conditions = {
            "alligator_bullish": alligator_bullish,
            "ao_positive": ao_positive,
            "close_above_fractal": close_above_fractal,
            "valid_sl": valid_sl,
        }
        short_conditions = {
            "alligator_bearish": alligator_bearish,
            "ao_negative": ao_negative,
            "close_below_fractal": close_below_fractal,
            "valid_sl": valid_sl_short,
        }
        missing_long = [k for k, ok in long_conditions.items() if not ok]
        missing_short = [k for k, ok in short_conditions.items() if not ok]
        self._last_evaluation = SignalEvaluation(
            symbol=symbol,
            timeframe=timeframe,
            decision="NO_SIGNAL",
            signal_generated=False,
            reason=(
                f"long_missing:{','.join(missing_long)};"
                f"short_missing:{','.join(missing_short)}"
            ),
            candle_open_time=last.get("open_time"),
            long_conditions=long_conditions,
            short_conditions=short_conditions,
        )
        logger.debug("no_signal", symbol=symbol, timeframe=timeframe)
        return None

    # ─── Alligator state helpers ──────────────────────────────────────────────

    @staticmethod
    def _is_alligator_bullish(jaw: float, teeth: float, lips: float, close: float) -> bool:
        """Bullish: lips > teeth > jaw and price above all three lines."""
        return lips > teeth > jaw and close > lips

    @staticmethod
    def _is_alligator_bearish(jaw: float, teeth: float, lips: float, close: float) -> bool:
        """Bearish: lips < teeth < jaw and price below all three lines."""
        return lips < teeth < jaw and close < lips
