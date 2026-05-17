from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MlSupportDecision:
    ml_enabled: bool
    ml_shadow_mode: bool
    ml_score: float | None
    ml_decision: str | None
    ml_reason: str | None
    ml_model_version: str | None


class MlOperationalSupportService:
    """Camada auxiliar de ML em shadow mode (sem impacto operacional)."""

    def __init__(
        self,
        *,
        enabled: bool,
        shadow_mode: bool,
        allowed_symbol_timeframes: set[str] | None = None,
        model_version: str = "ml-support-stub-v1",
    ) -> None:
        self._enabled = enabled
        self._shadow_mode = shadow_mode
        self._allowed = allowed_symbol_timeframes or set()
        self._model_version = model_version

    def evaluate(
        self,
        *,
        symbol: str,
        timeframe: str,
        engine_outcome: str,
        engine_reason: str | None,
    ) -> MlSupportDecision:
        if not self._enabled:
            return MlSupportDecision(
                ml_enabled=False,
                ml_shadow_mode=self._shadow_mode,
                ml_score=None,
                ml_decision=None,
                ml_reason=None,
                ml_model_version=None,
            )

        pair = f"{symbol.upper()}:{timeframe}"
        if self._allowed and pair not in self._allowed:
            return MlSupportDecision(
                ml_enabled=False,
                ml_shadow_mode=self._shadow_mode,
                ml_score=None,
                ml_decision=None,
                ml_reason="pair_not_in_canary_scope",
                ml_model_version=self._model_version,
            )

        score = self._score_stub(engine_outcome=engine_outcome, engine_reason=engine_reason)
        decision = "ALLOW" if score >= 0.55 else "ABSTAIN"
        if engine_reason == "regime_lateral_blocked":
            decision = "BLOCK"
        reason = engine_reason or f"score_based:{score:.2f}"
        return MlSupportDecision(
            ml_enabled=True,
            ml_shadow_mode=self._shadow_mode,
            ml_score=score,
            ml_decision=decision,
            ml_reason=reason,
            ml_model_version=self._model_version,
        )

    @staticmethod
    def _score_stub(*, engine_outcome: str, engine_reason: str | None) -> float:
        if engine_outcome == "signal_detected":
            return 0.72
        if engine_reason and engine_reason.startswith("checklist_not_satisfied:"):
            return 0.31
        if engine_reason == "regime_lateral_blocked":
            return 0.18
        return 0.48
