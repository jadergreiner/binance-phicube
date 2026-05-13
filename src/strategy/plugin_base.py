"""
Plugin base — StrategyPlugin (Template Method), SignalResult, NullSignalResult.

Define o contrato abstrato para plugins de estratégia e os tipos de retorno.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SignalResult:
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    metadata: dict | None = None

    def __bool__(self) -> bool:
        return True


@dataclass(frozen=True)
class NullSignalResult:
    reason: str = ""
    metadata: dict | None = None

    def __bool__(self) -> bool:
        return False


class StrategyPlugin(ABC):
    def __init__(self, risk_reward_ratio: float = 2.0) -> None:
        self._rrr = risk_reward_ratio
        self._plugin_name: str = ""

    def __init_subclass__(cls, **kwargs: dict) -> None:
        super().__init_subclass__(**kwargs)
        original_init = cls.__init__

        def __init_wrapper__(self, *args: float, **kwargs: float) -> None:
            original_init(self, *args, **kwargs)
            if not hasattr(self, "_rrr"):
                raise TypeError(
                    f"{cls.__name__} must call super().__init__(risk_reward_ratio=...) "
                    "to properly initialize StrategyPlugin"
                )

        cls.__init__ = __init_wrapper__

    @property
    def name(self) -> str:
        return self._plugin_name or type(self).__name__

    @property
    def risk_reward_ratio(self) -> float:
        return self._rrr

    @abstractmethod
    def warmup_candles(self) -> int: ...

    async def evaluate(
        self, symbol: str, timeframe: str, df: pd.DataFrame
    ) -> SignalResult | NullSignalResult:
        try:
            enriched = self._compute_indicators(df)
            conditions = self._check_conditions(symbol, timeframe, enriched)
            if conditions is None:
                return NullSignalResult(reason="conditions_not_met")
            targets = self._calculate_targets(conditions, enriched)
            confidence = self._calculate_confidence(conditions, enriched)
            return self._build_result(conditions, targets, confidence)
        except Exception:
            return NullSignalResult(reason="evaluation_error")

    @abstractmethod
    def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame: ...

    @abstractmethod
    def _check_conditions(self, symbol: str, timeframe: str, df: pd.DataFrame) -> dict | None: ...

    @abstractmethod
    def _calculate_targets(self, conditions: dict, df: pd.DataFrame) -> dict: ...

    @abstractmethod
    def _calculate_confidence(self, conditions: dict, df: pd.DataFrame) -> float: ...

    def _build_result(self, conditions: dict, targets: dict, confidence: float) -> SignalResult:
        metadata = conditions.get("metadata", {})
        metadata["confidence"] = confidence
        metadata["plugin"] = self.name
        return SignalResult(
            direction=conditions["direction"],
            entry_price=targets["entry_price"],
            stop_loss=targets["stop_loss"],
            take_profit=targets["take_profit"],
            metadata=metadata,
        )
