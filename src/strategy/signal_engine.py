"""
Motor de detecção de sinais — Chain of Responsibility + Observer.

Chain of Responsibility:
    Handle 1 — plugin configurado (SYMBOL_STRATEGY_MAP)
    Handle 2 — Williams fallback (sempre disponível)

Observer:
    Emite eventos EVALUATED, DETECTED, REJECTED para subscribers.

Compatibilidade retroativa:
    Direction e Signal mantidos como re-exports neste módulo até
    SPEC futura removê-los definitivamente.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

import pandas as pd

from src.common.result import Result, SignalError, ok
from src.common.serialization import auto_dict
from src.monitoring.logger import get_logger
from src.strategy.plugin_base import NullSignalResult, SignalResult
from src.strategy.plugin_registry import PluginRegistry

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)


# ─── Re-exports (compatibilidade retroativa) ───────────────────────────────


class Direction(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


@auto_dict
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


# ─── Observers ────────────────────────────────────────────────────────────────


class SignalEvent(StrEnum):
    EVALUATED = "evaluated"
    DETECTED = "detected"
    REJECTED = "rejected"


@auto_dict
@dataclass(frozen=True)
class SignalEventData:
    event: SignalEvent
    symbol: str
    timeframe: str
    result: SignalResult | NullSignalResult
    duration_ms: float = 0.0


# ─── Module-level helpers (importáveis por plugins) ─────────────────────────


def is_alligator_bullish(jaw: float, teeth: float, lips: float, close: float) -> bool:
    """Bullish: lips > teeth > jaw and price above all three lines."""
    return lips > teeth > jaw and close > lips


def is_alligator_bearish(jaw: float, teeth: float, lips: float, close: float) -> bool:
    """Bearish: lips < teeth < jaw and price below all three lines."""
    return lips < teeth < jaw and close < lips


# ─── SignalEngine ─────────────────────────────────────────────────────────────


class SignalEngine:
    """Chain of Responsibility: config-plugin → williams-fallback + Observer events.

    Stateless: nenhum _last_evaluation (INV-033-07).
    evaluate() sempre retorna SignalResult | NullSignalResult, nunca None.
    """

    def __init__(
        self,
        plugin_registry: PluginRegistry | None = None,
        default_strategy: str = "williams",
        risk_reward_ratio: float = 2.0,
        symbol_strategy_map: dict[str, str] | None = None,
    ) -> None:
        self._registry = plugin_registry
        self._default_strategy = default_strategy
        self._rrr = risk_reward_ratio
        self._symbol_strategy_map = symbol_strategy_map or {}
        self._observers: dict[SignalEvent, list[Callable[[SignalEventData], None]]] = {
            e: [] for e in SignalEvent
        }
        self._regime_ao_abs_min = 0.01
        self._regime_alligator_spread_min = 0.0005

    # Backward compat: staticmethods que delegam para as functions module-level
    _is_alligator_bullish = staticmethod(is_alligator_bullish)
    _is_alligator_bearish = staticmethod(is_alligator_bearish)

    def on(self, evt: SignalEvent, callback: Callable[[SignalEventData], None]) -> None:
        self._observers[evt].append(callback)

    def _emit(self, data: SignalEventData) -> None:
        for cb in self._observers[data.event]:
            try:
                cb(data)
            except Exception as exc:
                logger.warning(
                    "observer_failed",
                    event_name=data.event.value,
                    error_type=type(exc).__name__,
                )

    async def evaluate(
        self,
        symbol: str,
        timeframe: str,
        df: pd.DataFrame,
    ) -> Result[SignalResult | NullSignalResult, SignalError]:
        if self._registry is None:
            logger.warning("no_plugin_registry", symbol=symbol, timeframe=timeframe)
            result: SignalResult | NullSignalResult = NullSignalResult(reason="no_plugin_registry")
            self._emit(SignalEventData(SignalEvent.REJECTED, symbol, timeframe, result))
            return ok(result)

        if len(df) < 50:
            logger.debug("insufficient_candles", symbol=symbol, rows=len(df))
            result = NullSignalResult(reason="insufficient_candles")
            self._emit(SignalEventData(SignalEvent.REJECTED, symbol, timeframe, result))
            return ok(result)

        # Chain of Responsibility
        chain = self._build_chain(symbol)
        result = NullSignalResult(reason="no_plugin_matched")
        selected_strategy_name: str | None = None
        for strategy_name, handler in chain:
            candidate = await handler.evaluate(symbol, timeframe, df)
            if isinstance(candidate, SignalResult):
                result = candidate
                selected_strategy_name = strategy_name
                break
            if isinstance(candidate, NullSignalResult):
                result = candidate  # keep last handler's reason

        if result and isinstance(result, SignalResult):
            gate_result = self._apply_regime_and_checklist_gate(
                df=df,
                signal=result,
                strategy_name=selected_strategy_name,
            )
            if isinstance(gate_result, NullSignalResult):
                result = gate_result
                self._emit(SignalEventData(SignalEvent.REJECTED, symbol, timeframe, result))
                return ok(result)
            self._emit(SignalEventData(SignalEvent.DETECTED, symbol, timeframe, result))
        else:
            self._emit(SignalEventData(SignalEvent.EVALUATED, symbol, timeframe, result))

        return ok(result)

    def _build_chain(self, symbol: str) -> list[tuple[str, object]]:
        handlers: list[tuple[str, object]] = []
        if self._registry is not None:
            strategy_name = self._symbol_strategy_map.get(symbol, self._default_strategy)
            plugin = self._registry.get(strategy_name)
            if plugin is not None:
                handlers.append((strategy_name, plugin))
                if strategy_name == "williams":
                    return handlers
            fallback = self._registry.get("williams")
            has_williams = any(name == "williams" for name, _handler in handlers)
            if fallback is not None and not has_williams:
                handlers.append(("williams", fallback))
        return handlers

    def _apply_regime_and_checklist_gate(
        self,
        *,
        df: pd.DataFrame,
        signal: SignalResult,
        strategy_name: str | None,
    ) -> SignalResult | NullSignalResult:
        if strategy_name != "williams":
            return signal
        direction = str(signal.direction or "").upper()
        if direction not in {"LONG", "SHORT"}:
            return NullSignalResult(reason="invalid_signal_direction")

        latest = df.iloc[-1]
        if self._is_lateral_regime(latest):
            return NullSignalResult(reason="regime_lateral_blocked")

        checklist = self._evaluate_bo_williams_checklist(latest, direction, df=df)
        missing = [item for item, ok_flag in checklist.items() if not ok_flag]
        if missing:
            return NullSignalResult(
                reason=f"checklist_not_satisfied:{','.join(missing)}",
                metadata={"checklist": checklist},
            )
        return signal

    def _is_lateral_regime(self, latest: pd.Series) -> bool:
        ao = self._to_float_or_none(latest.get("ao"))
        jaw = self._to_float_or_none(latest.get("jaw"))
        teeth = self._to_float_or_none(latest.get("teeth"))
        lips = self._to_float_or_none(latest.get("lips"))
        if ao is None or jaw is None or teeth is None or lips is None:
            return False
        spread = abs(lips - teeth) + abs(teeth - jaw)
        return abs(ao) < self._regime_ao_abs_min and spread < self._regime_alligator_spread_min

    def _evaluate_bo_williams_checklist(
        self,
        latest: pd.Series,
        direction: str,
        df: pd.DataFrame | None = None,
    ) -> dict[str, bool]:
        close = self._to_float_or_none(latest.get("close"))
        jaw = self._to_float_or_none(latest.get("jaw"))
        teeth = self._to_float_or_none(latest.get("teeth"))
        lips = self._to_float_or_none(latest.get("lips"))
        ao = self._to_float_or_none(latest.get("ao"))
        fractal_high = self._resolve_recent_fractal(df=df, latest=latest, column="fractal_high")
        fractal_low = self._resolve_recent_fractal(df=df, latest=latest, column="fractal_low")

        if direction == "LONG":
            return {
                "alligator_aligned": bool(
                    close is not None
                    and jaw is not None
                    and teeth is not None
                    and lips is not None
                    and is_alligator_bullish(jaw, teeth, lips, close)
                ),
                "ao_confirmed": bool(ao is not None and ao > 0),
                "fractal_valid": bool(
                    fractal_low is not None and close is not None and fractal_low < close
                ),
            }
        return {
            "alligator_aligned": bool(
                close is not None
                and jaw is not None
                and teeth is not None
                and lips is not None
                and is_alligator_bearish(jaw, teeth, lips, close)
            ),
            "ao_confirmed": bool(ao is not None and ao < 0),
            "fractal_valid": bool(
                fractal_high is not None and close is not None and fractal_high > close
            ),
        }

    def _resolve_recent_fractal(
        self,
        *,
        df: pd.DataFrame | None,
        latest: pd.Series,
        column: str,
        lookback: int = 6,
    ) -> float | None:
        direct = self._to_float_or_none(latest.get(column))
        if direct is not None:
            return direct
        if df is None or column not in df.columns:
            return None
        tail = df[column].tail(lookback)
        for value in reversed(tail.tolist()):
            numeric = self._to_float_or_none(value)
            if numeric is not None:
                return numeric
        return None

    @staticmethod
    def _to_float_or_none(value: object) -> float | None:
        try:
            numeric = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        if pd.isna(numeric):
            return None
        return numeric

    @staticmethod
    def last_evaluation() -> None:
        """Placeholder — SignalEngine é stateless desde SPEC_033.

        Antigo _last_evaluation removido. Consumidores devem usar
        Observer events ou o retorno direto de evaluate().
        """
        return None
