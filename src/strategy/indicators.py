"""
Indicadores técnicos da estratégia BO Williams (Phicube).

Implementados sem dependências externas além de pandas/numpy para
garantir total controle sobre os cálculos e rastreabilidade.

Indicadores:
    - Alligator de Bill Williams (Jaw, Teeth, Lips via SMMA)
    - Awesome Oscillator (AO)
    - Fractais de Bill Williams (Bullish e Bearish)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# ─── Constants ────────────────────────────────────────────────────────────────

_DEFAULT_LOOKBACK = 100

# ─── Alligator ────────────────────────────────────────────────────────────────


def smma(series: pd.Series, period: int) -> pd.Series:
    """Smoothed Moving Average (SMMA / Wilder's MA / RMA).

    SMMA[0] = SMA(period)
    SMMA[i] = (SMMA[i-1] * (period - 1) + series[i]) / period
    """
    result = np.full(len(series), np.nan)
    values = series.to_numpy(dtype=float)

    # Seed with SMA
    seed_end = period - 1
    if len(values) < period:
        return pd.Series(result, index=series.index)

    result[seed_end] = np.mean(values[:period])

    for i in range(period, len(values)):
        result[i] = (result[i - 1] * (period - 1) + values[i]) / period

    return pd.Series(result, index=series.index)


def alligator(df: pd.DataFrame, *, inplace: bool = False) -> pd.DataFrame:
    """Calculate Bill Williams Alligator on a OHLCV DataFrame.

    Uses the median price (HL/2) as input.

    When inplace=True, modifies the original DataFrame and returns it
    (no copy). Default behavior (inplace=False) returns a copy.

    Returns a DataFrame with added columns:
        jaw    — 13-period SMMA, shifted 8 bars forward
        teeth  — 8-period SMMA, shifted 5 bars forward
        lips   — 5-period SMMA, shifted 3 bars forward
    """
    median = (df["high"] + df["low"]) / 2.0

    jaw_raw = smma(median, 13)
    teeth_raw = smma(median, 8)
    lips_raw = smma(median, 5)

    out = df if inplace else df.copy()
    out["jaw"] = jaw_raw.shift(8)
    out["teeth"] = teeth_raw.shift(5)
    out["lips"] = lips_raw.shift(3)
    return out


# ─── Awesome Oscillator ───────────────────────────────────────────────────────


def awesome_oscillator(df: pd.DataFrame, *, inplace: bool = False) -> pd.DataFrame:
    """Calculate the Awesome Oscillator (AO).

    AO = SMA(median_price, 5) - SMA(median_price, 34)

    When inplace=True, modifies the original DataFrame and returns it.
    Default behavior (inplace=False) returns a copy.

    Returns a DataFrame with added column: ao
    """
    median = (df["high"] + df["low"]) / 2.0
    out = df if inplace else df.copy()
    out["ao"] = median.rolling(window=5).mean() - median.rolling(window=34).mean()
    return out


# ─── Fractais ─────────────────────────────────────────────────────────────────


def _fractals_inplace(highs: np.ndarray, lows: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute fractal arrays in-place (no DataFrame copy)."""
    n = len(highs)
    fractal_high = np.full(n, np.nan)
    fractal_low = np.full(n, np.nan)

    for i in range(2, n - 2):
        window_h = highs[i - 2 : i + 3]
        if highs[i] == np.max(window_h) and np.sum(window_h == highs[i]) == 1:
            fractal_high[i] = highs[i]

        window_l = lows[i - 2 : i + 3]
        if lows[i] == np.min(window_l) and np.sum(window_l == lows[i]) == 1:
            fractal_low[i] = lows[i]

    return fractal_high, fractal_low


def fractals(df: pd.DataFrame, *, inplace: bool = False) -> pd.DataFrame:
    """Detect Bill Williams Fractals (5-bar pattern).

    Bearish fractal (resistance): bar[i] has the HIGHEST high among
        bar[i-2], bar[i-1], bar[i], bar[i+1], bar[i+2].

    Bullish fractal (support): bar[i] has the LOWEST low among
        bar[i-2], bar[i-1], bar[i], bar[i+1], bar[i+2].

    When inplace=True, modifies the original DataFrame and returns it.
    Default behavior (inplace=False) returns a copy.

    Returns a DataFrame with added columns:
        fractal_high  — price of bearish fractal (NaN if not a fractal)
        fractal_low   — price of bullish fractal (NaN if not a fractal)

    Note: The most recent 2 bars can never be fractals (require future bars).
    """
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)

    fractal_high, fractal_low = _fractals_inplace(highs, lows)

    out = df if inplace else df.copy()
    out["fractal_high"] = fractal_high
    out["fractal_low"] = fractal_low
    return out


# ─── Pipeline completo ────────────────────────────────────────────────────────


def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all indicators to a OHLCV DataFrame in one call.

    Legacy wrapper — delegates to compute_all_optimized().
    """
    return compute_all_optimized(df)


def compute_all_optimized(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all indicators with a single DataFrame copy.

    Replaces 3 separate df.copy() calls with 1 copy, reducing
    memory allocations by ~3x.

    When inplace=True on individual functions, the copy is made
    once up-front and all modifications are in-place.
    """
    out = df.copy()
    alligator(out, inplace=True)
    awesome_oscillator(out, inplace=True)
    fractals(out, inplace=True)
    return out


# ─── ATR (Average True Range) — SPEC_029 ──────────────────────────────────────


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """True Range: max(high - low, abs(high - prev_close), abs(low - prev_close)).

    O primeiro TR é sempre NaN (não há prev_close para o candle 0).
    """
    prev_close = close.shift(1)
    return pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1, skipna=False)


def atr(
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    period: int = 14,
) -> pd.Series:
    """Average True Range — Wilder's smoothed ATR (SMMA of True Range).

    Implementação: SMMA do True Range (média móvel suavizada de Wilder).
    Diferente de SMA porque o primeiro valor é SMA e os seguintes são
    atualizados recursivamente:
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period

    Retorna pd.Series mesmo comprimento que entrada.
    NaN nos primeiros ``period`` candles.

    Args:
        close: Série de preços de fechamento.
        high: Série de preços máximos.
        low: Série de preços mínimos.
        period: Período do ATR (default 14).

    Returns:
        pd.Series com valores ATR.
    """
    tr = _true_range(high, low, close)
    atr_values = pd.Series(index=close.index, dtype=float)

    if len(tr) <= period:
        return atr_values  # todos NaN

    # Primeiro ATR: SMA dos primeiros `period` TRs (índices 1..period)
    first_idx = period
    atr_values.iloc[first_idx] = tr.iloc[1 : period + 1].mean()

    # Demais valores: SMMA recursivo de Wilder
    for i in range(first_idx + 1, len(tr)):
        atr_values.iloc[i] = (atr_values.iloc[i - 1] * (period - 1) + tr.iloc[i]) / period

    return atr_values


# ─── _count_recent_crosses — SPEC_033 ─────────────────────────────────────────


def _count_recent_crosses(df: pd.DataFrame, lookback: int = 10) -> int:
    """Count how many times the AO crossed zero in the last N candles.

    The AO crosses zero when consecutive candles have opposite signs
    (positive → negative or negative → positive). A NaN value does
    NOT count as a cross.

    Returns:
        Number of zero-line crosses in the last ``lookback`` candles.
    """
    ao = df["ao"].iloc[-(lookback + 1) :]
    if len(ao) < 2:
        return 0
    signs = ao.dropna().apply(lambda v: 1 if v > 0 else -1)
    if len(signs) < 2:
        return 0
    diffs = signs.diff().fillna(0)
    return int((diffs != 0).sum())


# ─── Helper utilities ─────────────────────────────────────────────────────────


def last_valid_fractal_high(df: pd.DataFrame, lookback: int = 100) -> float | None:
    """Return the most recent bearish fractal high within lookback bars.

    Excludes the last 2 bars (cannot be fractals) and the last confirmed
    candle (index -2 is the last closed candle; -3 and earlier are fractals).
    """
    # Slice: exclude last 2 rows (incomplete fractal window) and last open candle
    series = df["fractal_high"].iloc[-(lookback + 2) : -2]
    valid = series.dropna()
    return float(valid.iloc[-1]) if not valid.empty else None


def last_valid_fractal_low(df: pd.DataFrame, lookback: int = 100) -> float | None:
    """Return the most recent bullish fractal low within lookback bars."""
    series = df["fractal_low"].iloc[-(lookback + 2) : -2]
    valid = series.dropna()
    return float(valid.iloc[-1]) if not valid.empty else None
