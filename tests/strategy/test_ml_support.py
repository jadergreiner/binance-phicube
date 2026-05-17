from __future__ import annotations

from src.strategy.ml_support import MlOperationalSupportService


def test_ml_support_disabled_returns_inactive_payload() -> None:
    service = MlOperationalSupportService(enabled=False, shadow_mode=True)

    decision = service.evaluate(
        symbol="BTCUSDT",
        timeframe="15m",
        engine_outcome="no_signal",
        engine_reason=None,
    )

    assert decision.ml_enabled is False
    assert decision.ml_score is None
    assert decision.ml_decision is None


def test_ml_support_canary_scope_blocks_pair_outside_allowlist() -> None:
    service = MlOperationalSupportService(
        enabled=True,
        shadow_mode=True,
        allowed_symbol_timeframes={"ETHUSDT:15m"},
    )

    decision = service.evaluate(
        symbol="BTCUSDT",
        timeframe="15m",
        engine_outcome="signal_detected",
        engine_reason=None,
    )

    assert decision.ml_enabled is False
    assert decision.ml_reason == "pair_not_in_canary_scope"


def test_ml_support_regime_lateral_forces_block_decision() -> None:
    service = MlOperationalSupportService(enabled=True, shadow_mode=True)

    decision = service.evaluate(
        symbol="BTCUSDT",
        timeframe="15m",
        engine_outcome="no_signal",
        engine_reason="regime_lateral_blocked",
    )

    assert decision.ml_enabled is True
    assert decision.ml_decision == "BLOCK"
    assert decision.ml_score == 0.18
