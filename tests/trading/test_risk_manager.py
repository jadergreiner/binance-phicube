from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd
import pytest

from src.config.settings import SizingMode
from src.strategy.signal_engine import Direction, Signal
from src.trading.risk_manager import PositionSize, RiskManager


def _signal(
    *,
    entry: float = 100.0,
    stop: float = 95.0,
    take_profit: float = 110.0,
    direction: Direction = Direction.LONG,
) -> Signal:
    return Signal(
        symbol="BTCUSDT",
        timeframe="4h",
        direction=direction,
        entry_price=entry,
        stop_loss=stop,
        take_profit=take_profit,
        fractal_ref=96.0,
    )


class TestRiskManager:
    def test_calculate_success_without_scaling(self) -> None:
        manager = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=10,
            max_capital_allocation_pct=50.0,
            min_notional=5.0,
        )
        signal = _signal(entry=100.0, stop=95.0)

        pos = manager.calculate(signal, available_balance=1000.0, quantity_precision=3)

        assert isinstance(pos, PositionSize)
        assert pos is not None
        assert pos.symbol == "BTCUSDT"
        assert pos.direction == Direction.LONG
        assert pos.quantity == 2.0
        assert pos.notional == 200.0
        assert pos.margin_required == 20.0
        assert pos.risk_amount == 10.0

    def test_calculate_scales_down_by_max_allocation(self) -> None:
        manager = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=2,
            max_capital_allocation_pct=10.0,
            min_notional=5.0,
        )
        signal = _signal(entry=100.0, stop=99.0, take_profit=102.0)

        pos = manager.calculate(signal, available_balance=1000.0, quantity_precision=3)

        assert pos is None

    def test_returns_none_for_zero_stop_distance(self) -> None:
        manager = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=5,
            max_capital_allocation_pct=30.0,
        )
        signal = _signal(entry=100.0, stop=100.0)

        assert manager.calculate(signal, available_balance=1000.0) is None
        rejection = manager.consume_last_rejection()
        assert rejection is not None
        assert rejection.code == "ZERO_STOP_DISTANCE"
        assert rejection.reason == "stop_distance_zero"

    def test_returns_none_when_rounding_turns_qty_zero(self) -> None:
        manager = RiskManager(
            risk_per_trade_pct=0.001,
            leverage=20,
            max_capital_allocation_pct=100.0,
            min_notional=0.0,
        )
        signal = _signal(entry=100.0, stop=50.0)

        # raw qty is tiny and rounds to 0 with precision=3
        assert manager.calculate(signal, available_balance=100.0, quantity_precision=3) is None
        rejection = manager.consume_last_rejection()
        assert rejection is not None
        assert rejection.code == "QTY_ZERO_AFTER_ROUNDING"

    def test_returns_none_when_below_min_notional(self) -> None:
        manager = RiskManager(
            risk_per_trade_pct=0.1,
            leverage=20,
            max_capital_allocation_pct=100.0,
            min_notional=50.0,
        )
        signal = _signal(entry=100.0, stop=90.0)

        # qty should be 0.01, notional=1.0 < min_notional
        assert manager.calculate(signal, available_balance=100.0, quantity_precision=3) is None
        rejection = manager.consume_last_rejection()
        assert rejection is not None
        assert rejection.code == "MIN_NOTIONAL_NOT_MET"

    def test_loga_warning_quando_excede_max_capital_allocation(self, capsys) -> None:
        manager = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=2,
            max_capital_allocation_pct=10.0,
            min_notional=5.0,
        )
        signal = _signal(entry=100.0, stop=99.0, take_profit=102.0)

        pos = manager.calculate(signal, available_balance=1000.0, quantity_precision=3)
        captured = capsys.readouterr()

        assert pos is None
        assert "position_rejected" in captured.out
        assert "max_capital_allocation_exceeded" in captured.out
        rejection = manager.consume_last_rejection()
        assert rejection is not None
        assert rejection.code == "MAX_CAPITAL_ALLOCATION_EXCEEDED"

    def test_position_to_dict(self) -> None:
        manager = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=10,
            max_capital_allocation_pct=50.0,
        )
        signal = _signal(entry=100.0, stop=95.0)

        pos = manager.calculate(signal, available_balance=1000.0, quantity_precision=3)
        assert pos is not None

        payload = pos.to_dict()
        assert payload["symbol"] == "BTCUSDT"
        assert payload["direction"] == "LONG"
        assert payload["quantity"] == 2.0
        assert payload["risk_amount"] == 10.0
        assert manager.last_rejection is None

    def test_returns_none_when_intraday_loss_limit_reached(self) -> None:
        manager = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=10,
            max_capital_allocation_pct=50.0,
            intraday_loss_limit_pct=10.0,
        )
        signal = _signal(entry=100.0, stop=95.0)

        pos = manager.calculate(
            signal,
            available_balance=1000.0,
            quantity_precision=3,
            intraday_realized_pnl_usdt=-100.0,
            now_utc=datetime(2026, 5, 8, 12, 0, tzinfo=UTC),
        )

        assert pos is None
        rejection = manager.consume_last_rejection()
        assert rejection is not None
        assert rejection.code == "INTRADAY_LOSS_LIMIT_REACHED"
        assert rejection.reason == "intraday_loss_limit_reached"

    def test_intraday_lock_resets_on_next_day(self) -> None:
        manager = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=10,
            max_capital_allocation_pct=50.0,
            intraday_loss_limit_pct=10.0,
        )
        signal = _signal(entry=100.0, stop=95.0)

        blocked = manager.calculate(
            signal,
            available_balance=1000.0,
            quantity_precision=3,
            intraday_realized_pnl_usdt=-120.0,
            now_utc=datetime(2026, 5, 8, 12, 0, tzinfo=UTC),
        )
        assert blocked is None

        reopened = manager.calculate(
            signal,
            available_balance=1000.0,
            quantity_precision=3,
            intraday_realized_pnl_usdt=0.0,
            now_utc=datetime(2026, 5, 9, 12, 0, tzinfo=UTC),
        )
        assert isinstance(reopened, PositionSize)


# ═════════════════════════════════════════════════════════════════════
# SPEC_029 — Position Sizing por ATR
# ═════════════════════════════════════════════════════════════════════


def _atr_df(
    n: int = 20,
    close: float = 100.0,
    high_low_range: float = 2.0,
) -> pd.DataFrame:
    """Cria DataFrame OHLCV com ATR deterministico para testes.

    Com high/low constante, TR = high_low_range para todos os candles,
    e ATR (Wilder SMMA period=N) = high_low_range a partir do indice N-1.
    """
    return pd.DataFrame(
        {
            "open": [close] * n,
            "high": [close + high_low_range / 2] * n,
            "low": [close - high_low_range / 2] * n,
            "close": [close] * n,
            "volume": [1000.0] * n,
        }
    )


class TestRiskManagerATR:
    """SPEC_029 — Position Sizing por ATR (modo atr_with_guard)."""

    # ── Guard: atr_with_guard ──────────────────────────────────────

    def test_atr_guard_posicao_menor_volatilidade_alta(self) -> None:
        """TEST_029_03: atr_with_guard — posição menor em alta volatilidade.

        ATR=2.0, fractal_sl=1.0 → effective_stop = max(1, 2*1.5) = 3.0.
        position_usdt = 10 * 100 / 3 = 333.33 → qty = 3.333
        """
        df = _atr_df(n=20, close=100.0, high_low_range=2.0)
        rm = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=10,
            max_capital_allocation_pct=50.0,
            sizing_mode=SizingMode.ATR,
            risk_per_trade_usdt=10.0,
            atr_period=14,
            atr_multiplier=1.5,
            min_position_usdt=10.0,
            max_position_usdt=500.0,
        )
        signal = _signal(entry=100.0, stop=99.0)  # stop_distance = 1.0

        pos = rm.calculate(signal, available_balance=1000.0, quantity_precision=3, df=df)

        assert pos is not None
        assert pos.quantity == 3.333
        assert pos.risk_amount == 10.0

    def test_atr_guard_fractal_domina(self) -> None:
        """TEST_029_04: guard when fractal_sl_distance > atr * multiplier.

        ATR=0.5, fractal_sl=3.0 → effective_stop = max(3, 0.5*1.5) = 3.0 = fractal.
        """
        df = _atr_df(n=20, close=100.0, high_low_range=0.5)
        rm = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=10,
            max_capital_allocation_pct=50.0,
            sizing_mode=SizingMode.ATR,
            risk_per_trade_usdt=10.0,
            atr_period=14,
            atr_multiplier=1.5,
            min_position_usdt=10.0,
            max_position_usdt=500.0,
        )
        signal = _signal(entry=100.0, stop=97.0)  # stop_distance = 3.0

        pos = rm.calculate(signal, available_balance=1000.0, quantity_precision=3, df=df)

        assert pos is not None
        # effective_stop = 3.0 (fractal domina)
        # position_usdt = 10 * 100 / 3 = 333.33 → qty = 3.333
        assert pos.quantity == 3.333

    def test_atr_guard_atr_domina(self) -> None:
        """TEST_029_05: ATR dominates when atr*multiplier >= fractal_sl_distance.

        ATR=4.0, fractal_sl=1.0 → effective_stop = max(1, 4*1.5) = 6.0 = atr*mult.
        """
        df = _atr_df(n=20, close=100.0, high_low_range=4.0)
        rm = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=10,
            max_capital_allocation_pct=50.0,
            sizing_mode=SizingMode.ATR,
            risk_per_trade_usdt=10.0,
            atr_period=14,
            atr_multiplier=1.5,
            min_position_usdt=10.0,
            max_position_usdt=500.0,
        )
        signal = _signal(entry=100.0, stop=99.0)  # stop_distance = 1.0

        pos = rm.calculate(signal, available_balance=1000.0, quantity_precision=3, df=df)

        assert pos is not None
        # effective_stop = 6.0 (ATR domina)
        # position_usdt = 10 * 100 / 6 = 166.67 → qty = 1.667
        assert pos.quantity == 1.667

    # ── Clamp parametrizado ────────────────────────────────────────

    @pytest.mark.parametrize(
        ("min_pos", "max_pos", "atr_range", "expected_qty"),
        [
            pytest.param(70.0, 1000.0, 10.0, 0.700, id="below_min"),
            pytest.param(10.0, 50.0, 2.0, 0.500, id="above_max"),
            pytest.param(10.0, 500.0, 2.0, 3.333, id="within_range"),
        ],
    )
    def test_atr_sizing_clamp(
        self,
        min_pos: float,
        max_pos: float,
        atr_range: float,
        expected_qty: float,
    ) -> None:
        """TEST_029_06: Clamp parametrizado.

        Formula:
            effective_stop = max(stop_dist, atr * multiplier)
            position_usdt = risk_usdt * entry / effective_stop
            clamped = clamp(position_usdt, min_pos, max_pos)
            qty = clamped / entry
        """
        risk_usdt = 10.0
        entry = 100.0
        mult = 1.5
        stop_dist = 0.01  # always < atr*mult, so ATR dominates

        df = _atr_df(n=20, close=entry, high_low_range=atr_range)

        rm = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=10,
            max_capital_allocation_pct=50.0,
            sizing_mode=SizingMode.ATR,
            risk_per_trade_usdt=risk_usdt,
            atr_period=14,
            atr_multiplier=mult,
            min_position_usdt=min_pos,
            max_position_usdt=max_pos,
        )
        signal = _signal(entry=entry, stop=entry - stop_dist)

        pos = rm.calculate(signal, available_balance=1000.0, quantity_precision=3, df=df)

        assert pos is not None
        assert pos.quantity == expected_qty, (
            f"min={min_pos} max={max_pos} range={atr_range}: "
            f"expected qty={expected_qty} got={pos.quantity}"
        )

    # ── Fallback ───────────────────────────────────────────────────

    @pytest.mark.parametrize(
        ("scenario", "df_factory"),
        [
            pytest.param("df_none", lambda: None, id="modo_atr_sem_df"),
            pytest.param(
                "atr_nan",
                lambda: _atr_df(n=5, close=100.0, high_low_range=2.0),
                id="atr_value_nan_poucas_candles",
            ),
            pytest.param(
                "atr_zero",
                lambda: _atr_df(n=20, close=100.0, high_low_range=0.0),
                id="atr_value_zero",
            ),
            pytest.param(
                "poucas_candles",
                lambda: _atr_df(n=13, close=100.0, high_low_range=2.0),
                id="candles_insuficientes_p_14",
            ),
        ],
    )
    def test_atr_fallback_para_fixed(
        self,
        scenario: str,
        df_factory: Any,
    ) -> None:
        """TEST_029_07: Fallback silencioso para fixed mode.

        Todos os cenarios devem resultar em position valida (fixed mode)
        quando ATR mode nao consegue calcular.
        """
        df = df_factory()
        rm = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=10,
            max_capital_allocation_pct=50.0,
            sizing_mode=SizingMode.ATR,
            risk_per_trade_usdt=10.0,
            atr_period=14,
            atr_multiplier=1.5,
            min_position_usdt=10.0,
            max_position_usdt=500.0,
        )
        signal = _signal(entry=100.0, stop=95.0)

        pos = rm.calculate(signal, available_balance=1000.0, quantity_precision=3, df=df)

        # Fallback silencioso: deve retornar PositionSize valido (modo fixed)
        assert pos is not None, f"Scenario '{scenario}' should fallback to fixed, got None"
        assert pos.risk_amount == 10.0  # fixed mode: risk = balance * pct = 1000 * 1% = 10

    # ── Fuzzing INV-029-05 ─────────────────────────────────────────

    @pytest.mark.parametrize("seed", list(range(100)))
    def test_inv_029_05_risco_real_nunca_excede_tolerancia(self, seed: int) -> None:
        """TEST_029_08: Fuzzing — invariante INV-029-05 em 100 cenarios.

        Garante que actual_risk_usdt <= risk_per_trade_usdt * 1.05
        para todos os cenarios aleatorios reproduziveis.

        Parametros sorteados por seed:
            entry_price: 1..50000
            stop_distance_pct: 0.5%..5% do entry
            atr_val_pct: 0.1%..2% do entry (antes da multiplicacao)
            multiplier: 1.0..5.0
            risk_usdt: 1..50
            min_pos: 5..50
            max_pos: 100..2000
        """
        rng = np.random.default_rng(seed)

        entry = rng.uniform(1.0, 50000.0)
        stop_dist_pct = rng.uniform(0.005, 0.05)
        stop_dist = entry * stop_dist_pct
        atr_val_pct = rng.uniform(0.001, 0.02)
        atr_val = entry * atr_val_pct
        multiplier = rng.uniform(1.0, 5.0)
        risk_usdt = rng.uniform(1.0, 50.0)
        min_pos = rng.uniform(5.0, 50.0)
        max_pos = rng.uniform(100.0, 2000.0)

        # Constroi DataFrame com ATR deterministico = atr_val
        df = _atr_df(n=20, close=entry, high_low_range=atr_val)

        rm = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=10,
            max_capital_allocation_pct=50.0,
            sizing_mode=SizingMode.ATR,
            risk_per_trade_usdt=risk_usdt,
            atr_period=14,
            atr_multiplier=multiplier,
            min_position_usdt=min_pos,
            max_position_usdt=max_pos,
        )

        # Usa stop_dist como fractal_sl para que effective_stop >= pelo menos isso
        signal = _signal(entry=entry, stop=entry - stop_dist)

        pos = rm.calculate(signal, available_balance=10000.0, quantity_precision=8, df=df)

        # Se position foi calculada, verifica invariante
        if pos is not None:
            # Recalcula effective_stop (nao exposto, mas sabemos a formula)
            eff_stop = max(stop_dist, atr_val * multiplier)
            actual_risk = pos.quantity * eff_stop
            max_risk = risk_usdt * 1.05
            assert actual_risk <= max_risk + 1e-9, (
                f"INV-029-05 VIOLATION seed={seed}: "
                f"actual_risk={actual_risk:.4f} > max_risk={max_risk:.4f} "
                f"(entry={entry:.2f} stop_dist={stop_dist:.4f} "
                f"atr={atr_val:.4f} mult={multiplier:.2f} "
                f"risk_usdt={risk_usdt:.2f})"
            )
        else:
            # Rejeicao pode acontecer (QTY_ZERO), mas nunca por INV-029-05
            rej = rm.consume_last_rejection()
            assert rej is None or rej.code != "INV_029_05_RISK_EXCEEDED", (
                f"seed={seed}: rejected by INV-029-05 unexpectedly. "
                f"Params: entry={entry:.2f} stop_dist={stop_dist:.4f} "
                f"atr={atr_val:.4f} mult={multiplier:.2f} "
                f"risk={risk_usdt:.2f} min={min_pos:.2f} max={max_pos:.2f}"
            )
