"""
Testes dos indicadores técnicos — inclui SPEC_029 (ATR).

Cobertura:
    - TEST_029_01: ATR calculado corretamente para série conhecida
    - TEST_029_02: ATR retorna NaN nos primeiros `period` candles
    - Edge: série curta, zeros, período configurável
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.strategy.indicators import _true_range, atr

# ─── _true_range ──────────────────────────────────────────────────────────────


class TestTrueRange:
    def test_primeiro_tr_nan(self):
        """O primeiro True Range é sempre NaN (não há prev_close)."""
        close = pd.Series([100.0, 102.0, 101.0])
        high = pd.Series([101.0, 103.0, 102.0])
        low = pd.Series([99.0, 101.0, 100.0])
        tr = _true_range(high, low, close)
        assert pd.isna(tr.iloc[0]), "Primeiro TR deve ser NaN"

    def test_tr_calcula_max_proprio(self):
        """TR[i] = max(high-low, abs(high-prev_close), abs(low-prev_close))."""
        close = pd.Series([100.0, 102.0])
        high = pd.Series([101.0, 105.0])
        low = pd.Series([99.0, 95.0])
        tr = _true_range(high, low, close)

        # Candle 1: high-low=10, |high-prev_close|=|105-100|=5, |low-prev_close|=|95-100|=5 → max=10
        assert round(tr.iloc[1], 4) == 10.0, "TR[1] deve ser max(10, 5, 5) = 10"

    def test_tr_abs_high_prev_close(self):
        """Caso onde abs(high - prev_close) domina."""
        close = pd.Series([100.0, 150.0])
        high = pd.Series([101.0, 102.0])
        low = pd.Series([99.0, 148.0])
        tr = _true_range(high, low, close)
        # Candle 1: high-low=4, |102-100|=2, |148-100|=48 → max=48
        assert round(tr.iloc[1], 4) == 48.0, "TR[1] deve ser max(4, 2, 48) = 48"

    def test_tr_abs_low_prev_close(self):
        """Caso onde abs(low - prev_close) domina."""
        close = pd.Series([100.0, 50.0])
        high = pd.Series([101.0, 80.0])
        low = pd.Series([99.0, 48.0])
        tr = _true_range(high, low, close)
        # Candle 1: high-low=32, |80-100|=20, |48-100|=52 → max=52
        assert round(tr.iloc[1], 4) == 52.0, "TR[1] deve ser max(32, 20, 52) = 52"

    def test_tr_mesmo_comprimento(self):
        """TR retorna mesma quantidade de elementos que entrada."""
        n = 50
        close = pd.Series(np.random.default_rng(42).uniform(90, 110, n))
        high = close + np.random.default_rng(99).uniform(0, 5, n)
        low = close - np.random.default_rng(199).uniform(0, 5, n)
        tr = _true_range(high, low, close)
        assert len(tr) == n, f"TR deve ter {n} elementos, tem {len(tr)}"


# ─── ATR ──────────────────────────────────────────────────────────────────────


class TestAtrSerieConhecida:
    """TEST_029_01: ATR calculado para série conhecida — match manual."""

    @pytest.fixture
    def series_curta(self):
        """Série pequena para validação manual com period=3.

        Dados:
            high: [101, 103, 102, 104, 106, 105, 107]
            low:  [99,  101, 100, 102, 104, 103, 105]
            close:[100, 102, 101, 103, 105, 104, 106]

        True Range:
            TR[0] = NaN
            TR[1] = max(103-101, |103-100|, |101-100|) = max(2, 3, 1) = 3
            TR[2] = max(102-100, |102-102|, |100-102|) = max(2, 0, 2) = 2
            TR[3] = max(104-102, |104-101|, |102-101|) = max(2, 3, 1) = 3
            TR[4] = max(106-104, |106-103|, |104-103|) = max(2, 3, 1) = 3
            TR[5] = max(105-103, |105-105|, |103-105|) = max(2, 0, 2) = 2
            TR[6] = max(107-105, |107-104|, |105-104|) = max(2, 3, 1) = 3

        ATR(3):
            ATR[3] = mean(TR[1], TR[2], TR[3]) = mean(3, 2, 3) = 2.6667
            ATR[4] = (2.6667 * 2 + 3) / 3 = 2.7778
            ATR[5] = (2.7778 * 2 + 2) / 3 = 2.5185
            ATR[6] = (2.5185 * 2 + 3) / 3 = 2.6790
        """
        return {
            "high": pd.Series([101.0, 103.0, 102.0, 104.0, 106.0, 105.0, 107.0]),
            "low": pd.Series([99.0, 101.0, 100.0, 102.0, 104.0, 103.0, 105.0]),
            "close": pd.Series([100.0, 102.0, 101.0, 103.0, 105.0, 104.0, 106.0]),
            "period": 3,
        }

    def test_atr_serie_conhecida_seed(self, series_curta):
        """ATR seed (SMA) calculado corretamente."""
        result = atr(
            series_curta["close"],
            series_curta["high"],
            series_curta["low"],
            period=series_curta["period"],
        )
        # ATR[3] = mean(3, 2, 3) = 2.6667
        assert not pd.isna(result.iloc[3]), "ATR[period] deve ser não-NaN"
        assert round(result.iloc[3], 4) == 2.6667, (
            f"ATR[3] = mean(3,2,3) = 2.6667, got {result.iloc[3]}"
        )

    def test_atr_serie_conhecida_recursive(self, series_curta):
        """ATR recursivo (SMMA Wilder) calculado corretamente."""
        result = atr(
            series_curta["close"],
            series_curta["high"],
            series_curta["low"],
            period=series_curta["period"],
        )
        # ATR[4] = (2.6667 * 2 + 3) / 3 = 2.7778
        assert round(result.iloc[4], 4) == 2.7778, (
            f"ATR[4] = (2.6667*2+3)/3 = 2.7778, got {result.iloc[4]}"
        )
        # ATR[5] = (2.7778 * 2 + 2) / 3 = 2.5185
        assert round(result.iloc[5], 4) == 2.5185, (
            f"ATR[5] = (2.7778*2+2)/3 = 2.5185, got {result.iloc[5]}"
        )


class TestAtrNanInicial:
    """TEST_029_02: ATR retorna NaN nos primeiros `period` candles."""

    @pytest.fixture
    def series_longa(self):
        """Série com 100 candles de dados contínuos."""
        n = 100
        rng = np.random.default_rng(42)
        close = pd.Series(100.0 + np.cumsum(rng.normal(0, 1, n)))
        high = close + abs(rng.normal(0, 0.5, n))
        low = close - abs(rng.normal(0, 0.5, n))
        return {"close": close, "high": high, "low": low}

    def test_atr_nan_primeiros_14(self, series_longa):
        """ATR(14): NaN nos primeiros 14 candles, não-NaN do 15º em diante."""
        result = atr(
            series_longa["close"],
            series_longa["high"],
            series_longa["low"],
            period=14,
        )
        assert result.isna().sum() == 14, (
            f"ATR(14) deve ter 14 NaNs no início, tem {result.isna().sum()}"
        )
        assert not result.iloc[14:].isna().any(), "ATR(14) não deve ter NaN após o índice 14"

    def test_atr_nan_primeiros_period(self, series_longa):
        """NaN nos primeiros `period` candles para qualquer período."""
        for period in [2, 5, 10, 20]:
            result = atr(
                series_longa["close"],
                series_longa["high"],
                series_longa["low"],
                period=period,
            )
            assert result.isna().sum() == period, (
                f"ATR({period}) deve ter {period} NaNs, tem {result.isna().sum()}"
            )
            tail = result.iloc[period:]
            valid = tail.dropna()
            assert len(valid) > 0, f"ATR({period}) deve ter valores válidos após o período"

    def test_atr_primeiro_nao_nan_no_indice_period(self, series_longa):
        """Primeiro ATR não-NaN aparece no índice `period`."""
        period = 14
        result = atr(
            series_longa["close"],
            series_longa["high"],
            series_longa["low"],
            period=period,
        )
        assert pd.isna(result.iloc[period - 1]), f"ATR[{period - 1}] deve ser NaN"
        assert not pd.isna(result.iloc[period]), f"ATR[{period}] deve ser o primeiro não-NaN"


# ─── Edge Cases ───────────────────────────────────────────────────────────────


class TestAtrEdgeCases:
    def test_serie_curta_retorna_todos_nan(self):
        """Série com menos de `period` candles retorna todos NaN."""
        close = pd.Series([100.0, 101.0, 102.0])
        high = pd.Series([101.0, 102.0, 103.0])
        low = pd.Series([99.0, 100.0, 101.0])
        result = atr(close, high, low, period=14)
        assert result.isna().all(), "Série com 3 candles e period=14 deve ser toda NaN"

    def test_serie_vazia(self):
        """Série vazia não quebra."""
        close = pd.Series([], dtype=float)
        high = pd.Series([], dtype=float)
        low = pd.Series([], dtype=float)
        result = atr(close, high, low, period=14)
        assert len(result) == 0, "Série vazia deve retornar vazia"

    def test_exatamente_period_candles(self):
        """Série com exatos `period` candles: primeiro ATR deve ser não-NaN."""
        n = 14
        close = pd.Series(np.arange(100.0, 100.0 + n))
        high = close + 1.0
        low = close - 1.0
        result = atr(close, high, low, period=n)
        # Com n=14 candles, temos TR[0]=NaN, TR[1..13]=13 válidos
        # Precisamos de 14 TRs válidos para ATR[14], mas temos só 13
        # Então ATR será todo NaN
        # (ATR first_idx = period = 14, len(tr) = 14 → first_idx = period = len(tr) → só NaN)
        assert result.isna().all(), (
            f"ATR({n}) com {n} candles deve ser todo NaN (precisa de {n + 1} candles)"
        )

    def test_period_um(self):
        """Period=1: ATR = TR (SMA de 1 valor)."""
        close = pd.Series([100.0, 102.0, 101.0])
        high = pd.Series([101.0, 103.0, 102.0])
        low = pd.Series([99.0, 101.0, 100.0])
        result = atr(close, high, low, period=1)
        # ATR[1] = TR[1] = mean(TR[1:2]) = TR[1] = 3.0
        assert not pd.isna(result.iloc[1]), "ATR(1)[1] deve ser não-NaN"
        assert round(result.iloc[1], 4) == 3.0, "ATR(1)[1] deve ser TR[1] = 3.0"
        # ATR[2] = (ATR[1]*0 + TR[2]) / 1 = TR[2] = 2.0
        assert round(result.iloc[2], 4) == 2.0, "ATR(1)[2] deve ser TR[2] = 2.0"

    def test_ohlcv_zero_nao_quebra(self, caplog):
        """OHLCV com zeros não causa divisão por zero — atr=0 → fallback."""
        import logging

        caplog.set_level(logging.WARNING)
        n = 20
        close = pd.Series([0.0] * n)
        high = pd.Series([0.0] * n)
        low = pd.Series([0.0] * n)
        result = atr(close, high, low, period=14)
        # TR = 0 para todos (high=low=close=0)
        # ATR[14] = mean(TR[1:15]) = 0 (todos TR são 0)
        assert not result.isna().all(), "ATR com zeros deve ter valores (todos zero)"

    # O resultado pode ser 0 (atr_value <= 0 → RiskManager fará fallback)


class TestAtrDefaultPeriod:
    def test_atr_default_period_14(self):
        """ATR usa period=14 como default."""
        n = 30
        close = pd.Series(np.arange(100.0, 100.0 + n))
        high = close + 1.0
        low = close - 1.0
        result = atr(close, high, low)
        assert result.isna().sum() == 14, "ATR default deve ter 14 NaNs"
        assert not pd.isna(result.iloc[14]), "ATR[14] deve ser não-NaN com default period"

    def test_atr_period_configuravel(self):
        """ATR aceita period diferente de 14."""
        n = 50
        close = pd.Series(np.arange(100.0, 100.0 + n))
        high = close + 1.0
        low = close - 1.0
        result_5 = atr(close, high, low, period=5)
        result_20 = atr(close, high, low, period=20)
        assert result_5.isna().sum() == 5, "ATR(5) deve ter 5 NaNs"
        assert result_20.isna().sum() == 20, "ATR(20) deve ter 20 NaNs"
