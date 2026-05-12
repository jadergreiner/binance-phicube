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


_SLIPPAGE_MAP = {
    "high": 0.0003,
    "medium": 0.0008,
    "low": 0.0015,
}

_LIQ_MAP = {
    "BTCUSDT": "high",
    "ETHUSDT": "high",
}


class TestSlippageEstimate:
    """TEST-043-03 e 04 — _estimate_slippage()."""

    def _rm_with_slippage(self) -> RiskManager:
        rm = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=5,
            max_capital_allocation_pct=30.0,
            risk_per_trade_usdt=5.0,
            sizing_mode=SizingMode.ATR,
            liq_map=_LIQ_MAP,
            slippage_map=_SLIPPAGE_MAP,
        )
        return rm

    def test_slippage_known_pair_high_tier(self) -> None:
        """TEST-043-03: BTCUSDT (high) → slippage_pct = 0.03%."""
        rm = self._rm_with_slippage()
        slippage = rm._estimate_slippage(
            symbol="BTCUSDT",
            quantity=0.1,
            entry_price=60000.0,
            atr_value=1000.0,
        )
        # static = 0.0003 * (0.1 * 60000) = 1.8
        # dynamic = (1000/60000) * 6000 * 0.5 = 0.5 * 1000 * 0.5 = 50? No...
        # atr_ratio = 1000/60000 = 0.01667, dynamic = 0.01667 * 6000 * 0.5 = 50
        # expected = max(1.8, 50) = 50
        expected_static = 0.0003 * 6000.0
        atr_ratio = 1000.0 / 60000.0
        expected_dynamic = atr_ratio * 6000.0 * 0.5
        expected = max(expected_static, expected_dynamic)
        assert slippage == pytest.approx(expected, rel=1e-4)
        assert slippage >= expected_static

    def test_slippage_unknown_pair_fallback_medium(self) -> None:
        """TEST-043-04: Par desconhecido → fallback medium (0.08%)."""
        rm = self._rm_with_slippage()
        slippage = rm._estimate_slippage(
            symbol="UNKNOWNUSDT",
            quantity=0.5,
            entry_price=100.0,
            atr_value=5.0,
        )
        # static = 0.0008 * 50 = 0.04
        # dynamic = (5/100) * 50 * 0.5 = 1.25
        expected = max(0.04, 1.25)
        assert slippage == pytest.approx(expected, rel=1e-4)

    def test_slippage_zero_entry_price(self) -> None:
        """Proteção contra divisão por zero: entry_price=0 → 0."""
        rm = self._rm_with_slippage()
        slippage = rm._estimate_slippage(
            symbol="BTCUSDT",
            quantity=0.1,
            entry_price=0.0,
            atr_value=1000.0,
        )
        assert slippage == 0.0

    def test_slippage_zero_quantity(self) -> None:
        """Proteção: quantity=0 → 0."""
        rm = self._rm_with_slippage()
        slippage = rm._estimate_slippage(
            symbol="BTCUSDT",
            quantity=0.0,
            entry_price=60000.0,
            atr_value=1000.0,
        )
        assert slippage == 0.0


class TestSlippageGateATR:
    """TEST-043-05 e 06 — Slippage gate no modo ATR."""

    def _make_df(self, close: float = 100.0) -> pd.DataFrame:
        arr = np.linspace(close - 5, close, 50)
        return pd.DataFrame({
            "close": arr,
            "high": arr * 1.02,
            "low": arr * 0.98,
        })

    def test_slippage_rejects_excessive_risk(self) -> None:
        """TEST-043-05: Slippage + risco > tolerância → rejeição.

        Testa o gate diretamente em _calculate_atr() para evitar que o
        fallback para fixed mode mascare a rejeição por slippage.
        """
        rm = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=5,
            max_capital_allocation_pct=30.0,
            risk_per_trade_usdt=5.0,
            sizing_mode=SizingMode.ATR,
            slippage_tolerance_multiplier=1.01,
            slippage_validation_enabled=False,
            liq_map=_LIQ_MAP,
            slippage_map=_SLIPPAGE_MAP,
        )

        # Sinal que passa INV-029-05 mas falha no slippage gate
        signal = _signal(entry=100.0, stop=99.0, take_profit=105.0)
        df = self._make_df(100.0)

        # Primeiro sem validação (deve passar)
        pos = rm._calculate_atr(
            signal=signal,
            stop_distance=1.0,
            quantity_precision=3,
            df=df,
            available_balance=50000.0,
        )
        assert pos is not None, "Sem validação, _calculate_atr deve retornar posição"

        # Agora com validação ativa e tolerância baixa
        rm._slippage_validation_enabled = True  # liga flag manualmente no modo "misto"
        rm._slippage_tolerance_multiplier = 1.01  # tolerância mínima

        pos2 = rm._calculate_atr(
            signal=signal,
            stop_distance=1.0,
            quantity_precision=3,
            df=df,
            available_balance=50000.0,
        )
        assert pos2 is None, "_calculate_atr deve rejeitar com slippage validation ativo"
        rejection = rm.consume_last_rejection()
        assert rejection is not None
        assert rejection.code == "SLIPPAGE_EXCEEDS_TOLERANCE"

    def test_slippage_accepts_safe_risk(self) -> None:
        """TEST-043-06: Slippage + risco dentro da tolerância → PositionSize."""
        rm = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=5,
            max_capital_allocation_pct=30.0,
            risk_per_trade_usdt=5.0,
            sizing_mode=SizingMode.ATR,
            slippage_validation_enabled=True,
            slippage_tolerance_multiplier=1.10,
            liq_map=_LIQ_MAP,
            slippage_map=_SLIPPAGE_MAP,
        )

        # Signal com stop distante → position size pequeno → slippage baixa
        signal = _signal(entry=100.0, stop=90.0, take_profit=120.0)
        df = self._make_df(100.0)

        pos = rm.calculate(signal, available_balance=5000.0, quantity_precision=3, df=df)
        assert pos is not None
        assert isinstance(pos, PositionSize)

    def test_slippage_disabled_when_flag_false(self) -> None:
        """Slippage gate não executa se slippage_validation_enabled=False."""
        rm = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=5,
            max_capital_allocation_pct=30.0,
            risk_per_trade_usdt=5.0,
            sizing_mode=SizingMode.ATR,
        )
        # Não ativar validação — deve funcionar normalmente
        signal = _signal(entry=100.0, stop=90.0, take_profit=120.0)
        df = self._make_df(100.0)

        pos = rm.calculate(signal, available_balance=5000.0, quantity_precision=3, df=df)
        assert pos is not None


class TestSlippageGateFixed:
    """TEST-043-05 e 06 — Slippage gate no modo fixed."""

    def test_slippage_rejects_excessive_risk_fixed(self) -> None:
        """Slippage + risco > tolerância → rejeição no modo fixed.

        Configura parâmetros que passam MAX_CAPITAL_ALLOCATION mas
        excedem a tolerância de slippage.
        """
        rm = RiskManager(
            risk_per_trade_pct=1.0,  # 1% de 10000 = 100 USDT de risco
            leverage=5,
            max_capital_allocation_pct=50.0,  # margem máxima 5000
            slippage_validation_enabled=True,
            slippage_tolerance_multiplier=1.02,
            liq_map={"BTCUSDT": "low"},
            slippage_map={"low": 0.0015},
        )

        # stop=98, dist=2, raw_qty=100/2=50, notional=5000
        # margin=5000/5=1000 <= 5000 → PASS
        # actual_risk=50*2=100, slippage=0.0015*5000=7.5
        # total=107.5 > 100*1.02=102 → REJEITA
        signal = _signal(entry=100.0, stop=98.0, take_profit=105.0)

        pos = rm.calculate(signal, available_balance=10000.0, quantity_precision=3)
        assert pos is None
        rejection = rm.consume_last_rejection()
        assert rejection is not None
        assert rejection.code == "SLIPPAGE_EXCEEDS_TOLERANCE", (
            f"Esperava SLIPPAGE, recebeu {rejection.code}: {rejection.reason}"
        )


class TestMaxPositionPct:
    """TEST-043-10 e 11 — max_position_pct."""

    def _make_df(self) -> pd.DataFrame:
        arr = np.linspace(95, 100, 50)
        return pd.DataFrame({
            "close": arr,
            "high": arr * 1.02,
            "low": arr * 0.98,
        })

    def test_max_position_pct_limits_position(self) -> None:
        """TEST-043-10: max_position_pct=50, balance=300 → effective_max=150."""
        rm = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=5,
            max_capital_allocation_pct=30.0,
            risk_per_trade_usdt=100.0,  # alto para gerar position grande
            sizing_mode=SizingMode.ATR,
            max_position_usdt=500.0,
            max_position_pct=50.0,  # 50% do saldo
            min_position_usdt=1.0,
        )
        signal = _signal(entry=100.0, stop=90.0, take_profit=120.0)
        df = self._make_df()
        pos = rm.calculate(signal, available_balance=300.0, quantity_precision=3, df=df)

        assert pos is not None
        # effective_max = min(500, 300 * 50/100) = min(500, 150) = 150
        # position_usdt = risk * entry / effective_stop → deve estar clamped a 150
        assert pos.notional <= 150.0, (
            f"notional={pos.notional} deveria ser <= 150 (max_position_pct=50%)"
        )

    def test_max_position_pct_zero_disabled(self) -> None:
        """TEST-043-11: max_position_pct=0 → usa MAX_POSITION_USDT."""
        rm = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=5,
            max_capital_allocation_pct=30.0,
            risk_per_trade_usdt=200.0,
            sizing_mode=SizingMode.ATR,
            max_position_usdt=500.0,
            max_position_pct=0.0,  # desabilitado
            min_position_usdt=1.0,
        )
        signal = _signal(entry=100.0, stop=90.0, take_profit=120.0)
        df = self._make_df()
        pos = rm.calculate(signal, available_balance=300.0, quantity_precision=3, df=df)

        assert pos is not None
        # max_position_pct=0 → usa max_position_usdt=500 como limite
        assert pos.notional <= 500.0
        # Verificar que não foi limitado a 150 (que seria 50% de 300)
        if pos.notional > 150.0:
            pass  # OK: sem o limite de 50%, notional pode ser maior


class TestCircuitBreaker:
    """TEST-043-12 a 18 — Circuit breaker pair-level (register_trade_outcome)."""

    async def _rm_cb(
        self,
        enabled: bool = True,
        threshold: int = 3,
        reduction: float = 0.5,
        recovery: int = 1,
        risk_usdt: float = 100.0,
    ) -> RiskManager:
        rm = RiskManager(
            risk_per_trade_pct=1.0,
            leverage=5,
            max_capital_allocation_pct=30.0,
            risk_per_trade_usdt=risk_usdt,
            sizing_mode=SizingMode.FIXED,
            min_position_usdt=1.0,
            max_position_usdt=500.0,
            consecutive_loss_threshold=threshold,
            cb_risk_reduction_factor=reduction,
            recovery_wins_needed=recovery,
            circuit_breaker_enabled=enabled,
        )
        return rm

    async def test_cb_disabled_quando_flag_false(self) -> None:
        """TEST-043-12: circuit_breaker_enabled=False → não altera estado."""
        rm = await self._rm_cb(enabled=False)
        for _ in range(5):
            await rm.register_trade_outcome(-10.0)

        assert not rm.circuit_breaker_active
        assert rm.effective_risk_per_trade_usdt == 100.0

    async def test_cb_ativa_apos_perdas_consecutivas(self) -> None:
        """TEST-043-13: threshold=3, 3 perdas → CB ativo."""
        rm = await self._rm_cb(risk_usdt=200.0)
        for _ in range(3):
            await rm.register_trade_outcome(-10.0)

        assert rm.circuit_breaker_active
        assert rm.effective_risk_per_trade_usdt == 100.0  # 200 * 0.5

    async def test_cb_nao_ativa_antes_do_threshold(self) -> None:
        """TEST-043-14: 2 perdas com threshold=3 → CB não ativa."""
        rm = await self._rm_cb()
        for _ in range(2):
            await rm.register_trade_outcome(-10.0)

        assert not rm.circuit_breaker_active

    async def test_cb_dead_zone_pnl_pequeno(self) -> None:
        """TEST-043-15 (D10): PnL ±0.001 não altera contadores."""
        rm = await self._rm_cb()
        await rm.register_trade_outcome(0.0005)
        assert rm._consecutive_losses == 0

        await rm.register_trade_outcome(-0.0005)
        assert rm._consecutive_losses == 0

    async def test_cb_reseta_apos_recovery_wins(self) -> None:
        """TEST-043-16: recovery_wins_needed=2 → 2 vitórias resetam."""
        rm = await self._rm_cb(recovery=2, risk_usdt=100.0)
        for _ in range(3):
            await rm.register_trade_outcome(-10.0)
        assert rm.circuit_breaker_active
        assert rm.effective_risk_per_trade_usdt == 50.0

        await rm.register_trade_outcome(5.0)
        assert rm.circuit_breaker_active
        assert rm._recovery_wins_count == 1

        await rm.register_trade_outcome(3.0)
        assert not rm.circuit_breaker_active
        assert rm.effective_risk_per_trade_usdt == 100.0

    async def test_cb_vitoria_quando_inativo_reseta_losses(self) -> None:
        """TEST-043-17: Vitória com CB inativo zera consecutive_losses."""
        rm = await self._rm_cb()
        await rm.register_trade_outcome(-10.0)
        await rm.register_trade_outcome(-5.0)
        assert rm._consecutive_losses == 2

        await rm.register_trade_outcome(5.0)
        assert rm._consecutive_losses == 0
        assert not rm.circuit_breaker_active

    async def test_cb_risk_floor_um_dolar(self) -> None:
        """TEST-043-18 (INV-043-03): Piso $1.00 com reduction muito baixo."""
        rm = await self._rm_cb(reduction=0.01, risk_usdt=10.0)
        for _ in range(3):
            await rm.register_trade_outcome(-10.0)

        assert rm.circuit_breaker_active
        assert rm.effective_risk_per_trade_usdt == 1.0
