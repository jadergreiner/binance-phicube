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


class SignalEngine:
    """Evaluates a closed OHLCV DataFrame and returns a Signal or None."""

    def __init__(self, risk_reward_ratio: float = 2.0) -> None:
        self._rrr = risk_reward_ratio

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
            return None

        jaw, teeth, lips, ao = float(jaw), float(teeth), float(lips), float(ao)

        # ─── Long signal ──────────────────────────────────────────────────────
        if self._is_alligator_bullish(jaw, teeth, lips, close) and ao > 0:
            fractal_ref = last_valid_fractal_high(enriched)
            if fractal_ref is not None and close > fractal_ref:
                sl = last_valid_fractal_low(enriched)
                if sl is not None and sl < close:
                    tp = close + (close - sl) * self._rrr
                    signal = Signal(
                        symbol=symbol,
                        timeframe=timeframe,
                        direction=Direction.LONG,
                        entry_price=close,
                        stop_loss=sl,
                        take_profit=tp,
                        fractal_ref=fractal_ref,
                    )
                    logger.info("signal_detected", **signal.to_dict())
                    return signal

        # ─── Short signal ─────────────────────────────────────────────────────
        if self._is_alligator_bearish(jaw, teeth, lips, close) and ao < 0:
            fractal_ref = last_valid_fractal_low(enriched)
            if fractal_ref is not None and close < fractal_ref:
                sl = last_valid_fractal_high(enriched)
                if sl is not None and sl > close:
                    tp = close - (sl - close) * self._rrr
                    signal = Signal(
                        symbol=symbol,
                        timeframe=timeframe,
                        direction=Direction.SHORT,
                        entry_price=close,
                        stop_loss=sl,
                        take_profit=tp,
                        fractal_ref=fractal_ref,
                    )
                    logger.info("signal_detected", **signal.to_dict())
                    return signal

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
