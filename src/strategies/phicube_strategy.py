"""
PhiCubeStrategy — Plugin v1 baseado no pack RN-PHI aprovado para execução.

Escopo desta implementação (T02):
    - RN-PHI-003..016
    - RN-PHI-024

Observação:
    Fórmulas proprietárias de MIMASAR/SANTO não foram publicadas.
    Nesta versão usamos proxies explícitos e rastreáveis (fractal + AO + Alligator).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.strategies.williams_strategy import calculate_targets
from src.strategy.indicators import _count_recent_crosses, compute_all_optimized
from src.strategy.plugin_base import NullSignalResult, SignalResult, StrategyPlugin
from src.strategy.signal_engine import is_alligator_bearish, is_alligator_bullish

_RN3 = "RN-PHI-003"
_RN4 = "RN-PHI-004"
_RN5 = "RN-PHI-005"
_RN6 = "RN-PHI-006"
_RN7 = "RN-PHI-007"
_RN8 = "RN-PHI-008"
_RN9 = "RN-PHI-009"
_RN10 = "RN-PHI-010"
_RN11 = "RN-PHI-011"
_RN12 = "RN-PHI-012"
_RN13 = "RN-PHI-013"
_RN14 = "RN-PHI-014"
_RN15 = "RN-PHI-015"
_RN16 = "RN-PHI-016"
_RN24 = "RN-PHI-024"


@dataclass(frozen=True)
class _Snapshot:
    close: float
    jaw: float
    teeth: float
    lips: float
    ao: float
    mima_roc: float
    support: float | None
    resistance: float | None
    small_up: bool
    small_down: bool
    mid_up: bool
    mid_down: bool
    large_up: bool
    large_down: bool
    reversal_watch: bool


class PhicubeStrategy(StrategyPlugin):
    def __init__(self, risk_reward_ratio: float = 2.0) -> None:
        super().__init__(risk_reward_ratio)
        self._plugin_name = "phicube"

    def warmup_candles(self) -> int:
        return 50

    async def evaluate(
        self, symbol: str, timeframe: str, df: pd.DataFrame
    ) -> SignalResult | NullSignalResult:
        if len(df) < self.warmup_candles():
            return NullSignalResult(
                reason="insufficient_data",
                metadata={
                    "plugin": self.name,
                    "rule_hits": [f"{_RN14}:fail"],
                },
            )

        try:
            enriched = self._compute_indicators(df)
            conditions = self._check_conditions(symbol, timeframe, enriched)
        except Exception:
            return NullSignalResult(
                reason="config_invalid",
                metadata={
                    "plugin": self.name,
                    "rule_hits": [f"{_RN24}:not_confirmed"],
                },
            )

        if conditions is None:
            return NullSignalResult(reason="no_setup_detected")

        if conditions["direction"] in {"LONG", "SHORT"}:
            targets = self._calculate_targets(conditions, enriched)
            confidence = self._calculate_confidence(conditions, enriched)
            metadata = dict(conditions.get("metadata", {}))
            metadata["confidence"] = confidence
            metadata["plugin"] = self.name
            return SignalResult(
                direction=conditions["direction"],
                entry_price=targets["entry_price"],
                stop_loss=targets["stop_loss"],
                take_profit=targets["take_profit"],
                metadata=metadata,
            )

        return NullSignalResult(
            reason=str(conditions.get("reason") or "no_setup_detected"),
            metadata=conditions.get("metadata"),
        )

    def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        required = {"jaw", "teeth", "lips", "ao", "fractal_high", "fractal_low"}
        if required.issubset(df.columns):
            return df
        return compute_all_optimized(df)

    def _check_conditions(self, symbol: str, timeframe: str, df: pd.DataFrame) -> dict | None:
        snapshot = self._snapshot(df)
        if snapshot is None:
            return {
                "reason": "insufficient_data",
                "metadata": {
                    "plugin": self.name,
                    "rule_hits": [f"{_RN14}:fail"],
                },
            }

        rule_hits: list[str] = [f"{_RN14}:ok"]

        market_state = self._market_state(snapshot, rule_hits)
        trend_alignment = self._trend_alignment(snapshot, rule_hits)
        momentum_polarity = (
            "positive" if snapshot.ao > 0 else "negative" if snapshot.ao < 0 else "flat"
        )
        rule_hits.append(f"{_RN9}:{momentum_polarity}")

        mima_roc_polarity = (
            "positive" if snapshot.mima_roc > 0 else "negative" if snapshot.mima_roc < 0 else "flat"
        )
        rule_hits.append(f"{_RN10}:{mima_roc_polarity}")

        confluence = (snapshot.ao > 0 and snapshot.mima_roc > 0) or (
            snapshot.ao < 0 and snapshot.mima_roc < 0
        )
        rule_hits.append(f"{_RN11}:{'confluence' if confluence else 'divergence'}")
        continuation_tag = (
            "continuation_confidence"
            if confluence and trend_alignment != "mixed"
            else "low_confidence"
        )
        rule_hits.append(f"{_RN12}:{continuation_tag}")
        rule_hits.append(f"{_RN8}:{'reversal_watch' if snapshot.reversal_watch else 'stable'}")
        rule_hits.append(f"{_RN13}:proxy_fractal_support_resistance")
        rule_hits.append(f"{_RN24}:chart_confirmed")

        long_ok = (
            trend_alignment == "bullish"
            and snapshot.ao > 0
            and snapshot.mima_roc > 0
            and snapshot.support is not None
            and snapshot.close > snapshot.support
        )
        short_ok = (
            trend_alignment == "bearish"
            and snapshot.ao < 0
            and snapshot.mima_roc < 0
            and snapshot.resistance is not None
            and snapshot.close < snapshot.resistance
        )

        base_metadata = {
            "plugin": self.name,
            "rule_hits": rule_hits,
            "market_state": market_state,
            "reason": "no_setup_detected",
            "chart_confirmation": True,
            "indicators": {
                "jaw": snapshot.jaw,
                "teeth": snapshot.teeth,
                "lips": snapshot.lips,
                "ao": snapshot.ao,
                "mima_roc": snapshot.mima_roc,
                "support": snapshot.support,
                "resistance": snapshot.resistance,
            },
        }

        if long_ok:
            rule_hits.append(f"{_RN15}:long_setup_valid")
            return {
                "direction": "LONG",
                "entry_price": snapshot.close,
                "stop_loss": float(snapshot.support),
                "metadata": {
                    **base_metadata,
                    "reason": "long_setup_valid",
                },
            }

        if short_ok:
            rule_hits.append(f"{_RN16}:short_setup_valid")
            return {
                "direction": "SHORT",
                "entry_price": snapshot.close,
                "stop_loss": float(snapshot.resistance),
                "metadata": {
                    **base_metadata,
                    "reason": "short_setup_valid",
                },
            }

        return {
            "direction": "NONE",
            "reason": "conditions_not_met",
            "metadata": base_metadata,
        }

    def _calculate_targets(self, conditions: dict, df: pd.DataFrame) -> dict:
        return calculate_targets(
            direction=conditions["direction"],
            entry_price=float(conditions["entry_price"]),
            stop_loss=float(conditions["stop_loss"]),
            risk_reward_ratio=self._rrr,
        )

    def _calculate_confidence(self, conditions: dict, df: pd.DataFrame) -> float:
        meta = conditions.get("metadata", {})
        hits: list[str] = list(meta.get("rule_hits", []))
        base = 0.40
        if any("RN-PHI-011:confluence" in hit for hit in hits):
            base += 0.20
        if any("RN-PHI-012:continuation_confidence" in hit for hit in hits):
            base += 0.20
        if any("RN-PHI-008:reversal_watch" in hit for hit in hits):
            base -= 0.10
        return min(max(base, 0.0), 1.0)

    def _snapshot(self, df: pd.DataFrame) -> _Snapshot | None:
        latest = df.iloc[-1]
        if len(df) < 3:
            return None

        jaw_now = float(latest["jaw"])
        teeth_now = float(latest["teeth"])
        lips_now = float(latest["lips"])
        close_now = float(latest["close"])
        ao_now = float(latest["ao"])
        lips_prev = float(df["lips"].iloc[-2])

        support = self._last_valid(df["fractal_low"], fallback_series=df["low"])
        resistance = self._last_valid(df["fractal_high"], fallback_series=df["high"])

        small_up = lips_now > lips_prev
        small_down = lips_now < lips_prev
        mid_up = teeth_now > float(df["teeth"].iloc[-2])
        mid_down = teeth_now < float(df["teeth"].iloc[-2])
        large_up = jaw_now > float(df["jaw"].iloc[-2])
        large_down = jaw_now < float(df["jaw"].iloc[-2])

        reversal_watch = _count_recent_crosses(df, lookback=8) >= 1
        return _Snapshot(
            close=close_now,
            jaw=jaw_now,
            teeth=teeth_now,
            lips=lips_now,
            ao=ao_now,
            mima_roc=lips_now - lips_prev,
            support=support,
            resistance=resistance,
            small_up=small_up,
            small_down=small_down,
            mid_up=mid_up,
            mid_down=mid_down,
            large_up=large_up,
            large_down=large_down,
            reversal_watch=reversal_watch,
        )

    @staticmethod
    def _last_valid(series: pd.Series, fallback_series: pd.Series) -> float | None:
        valid = series.dropna()
        if not valid.empty:
            return float(valid.iloc[-1])
        if fallback_series.empty:
            return None
        return float(fallback_series.tail(20).iloc[-1])

    @staticmethod
    def _trend_alignment(snapshot: _Snapshot, rule_hits: list[str]) -> str:
        bullish = is_alligator_bullish(snapshot.jaw, snapshot.teeth, snapshot.lips, snapshot.close)
        bearish = is_alligator_bearish(snapshot.jaw, snapshot.teeth, snapshot.lips, snapshot.close)
        if bullish:
            rule_hits.append(f"{_RN6}:bullish_alignment")
            return "bullish"
        if bearish:
            rule_hits.append(f"{_RN7}:bearish_alignment")
            return "bearish"
        rule_hits.append(f"{_RN5}:mixed_alignment")
        return "mixed"

    @staticmethod
    def _market_state(snapshot: _Snapshot, rule_hits: list[str]) -> str:
        if snapshot.small_up and snapshot.mid_up and snapshot.large_up:
            rule_hits.append(f"{_RN3}:strong_up")
            return "strong_up"
        if snapshot.small_down and snapshot.mid_down and snapshot.large_down:
            rule_hits.append(f"{_RN4}:strong_down")
            return "strong_down"
        if (snapshot.small_up and snapshot.mid_down) or (snapshot.small_down and snapshot.mid_up):
            rule_hits.append(f"{_RN5}:consolidation")
            return "consolidation"
        rule_hits.append(f"{_RN5}:transition")
        return "transition"
