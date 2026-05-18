from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.monitoring.logger import get_logger
from src.strategy.plugin_base import NullSignalResult, SignalResult

logger = get_logger(__name__)


@dataclass(frozen=True)
class SignalEvaluationInput:
    symbol: str
    timeframe: str
    df: pd.DataFrame


@dataclass(frozen=True)
class SignalEvaluationOutput:
    signal_result: SignalResult | None
    decision: str
    reason: str | None = None
    metadata: dict[str, Any] | None = None
    error_type: str | None = None

    @property
    def has_signal(self) -> bool:
        return self.signal_result is not None


class SignalEngineBoundaryAdapter:
    """Boundary isolado para avaliação de sinal via SignalEngine."""

    def __init__(self, signal_engine: Any) -> None:
        self._signal_engine = signal_engine

    async def evaluate(self, payload: SignalEvaluationInput) -> SignalEvaluationOutput:
        if payload.df is None or payload.df.empty:
            logger.debug(
                "signal_boundary_invalid_input",
                symbol=payload.symbol,
                timeframe=payload.timeframe,
                reason="empty_dataframe",
            )
            return SignalEvaluationOutput(
                signal_result=None,
                decision="NO_SIGNAL",
                reason="empty_dataframe",
            )

        try:
            raw_result = await self._signal_engine.evaluate(
                payload.symbol,
                payload.timeframe,
                payload.df,
            )
            normalized = self._normalize_result(raw_result)
            if normalized.has_signal:
                logger.debug(
                    "signal_boundary_detected",
                    symbol=payload.symbol,
                    timeframe=payload.timeframe,
                    decision=normalized.decision,
                )
            else:
                logger.debug(
                    "signal_boundary_no_signal",
                    symbol=payload.symbol,
                    timeframe=payload.timeframe,
                    reason=normalized.reason,
                )
            return normalized
        except Exception as exc:
            logger.warning(
                "signal_boundary_evaluation_failed",
                symbol=payload.symbol,
                timeframe=payload.timeframe,
                error_type=type(exc).__name__,
            )
            return SignalEvaluationOutput(
                signal_result=None,
                decision="NO_SIGNAL",
                reason="signal_engine_exception",
                error_type=type(exc).__name__,
            )

    def consume_last_evaluation(self) -> Any:
        consume = getattr(self._signal_engine, "consume_last_evaluation", None)
        if callable(consume):
            return consume()
        return None

    def _normalize_result(self, raw_result: Any) -> SignalEvaluationOutput:
        if hasattr(raw_result, "is_err") and callable(raw_result.is_err):
            if raw_result.is_err():
                return SignalEvaluationOutput(
                    signal_result=None,
                    decision="NO_SIGNAL",
                    reason="signal_engine_result_err",
                )
            if hasattr(raw_result, "unwrap") and callable(raw_result.unwrap):
                raw_result = raw_result.unwrap()

        if isinstance(raw_result, SignalResult):
            direction = str(raw_result.direction).upper()
            if direction not in {"LONG", "SHORT"}:
                return SignalEvaluationOutput(
                    signal_result=None,
                    decision="NO_SIGNAL",
                    reason="invalid_signal_direction",
                )
            return SignalEvaluationOutput(
                signal_result=raw_result,
                decision=direction,
                metadata=raw_result.metadata if isinstance(raw_result.metadata, dict) else None,
            )

        if isinstance(raw_result, NullSignalResult):
            return SignalEvaluationOutput(
                signal_result=None,
                decision="NO_SIGNAL",
                reason=raw_result.reason or "no_signal",
                metadata=raw_result.metadata if isinstance(raw_result.metadata, dict) else None,
            )

        if raw_result is None:
            return SignalEvaluationOutput(
                signal_result=None,
                decision="NO_SIGNAL",
                reason="no_signal",
            )

        return SignalEvaluationOutput(
            signal_result=None,
            decision="NO_SIGNAL",
            reason=f"invalid_signal_result_type:{type(raw_result).__name__}",
        )
