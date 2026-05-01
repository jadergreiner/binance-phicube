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


def alligator(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate Bill Williams Alligator on a OHLCV DataFrame.

    Uses the median price (HL/2) as input.

    Returns a copy of df with added columns:
        jaw    — 13-period SMMA, shifted 8 bars forward
        teeth  — 8-period SMMA, shifted 5 bars forward
        lips   — 5-period SMMA, shifted 3 bars forward
    """
    median = (df["high"] + df["low"]) / 2.0

    jaw_raw = smma(median, 13)
    teeth_raw = smma(median, 8)
    lips_raw = smma(median, 5)

    out = df.copy()
    out["jaw"] = jaw_raw.shift(8)
    out["teeth"] = teeth_raw.shift(5)
    out["lips"] = lips_raw.shift(3)
    return out


# ─── Awesome Oscillator ───────────────────────────────────────────────────────


def awesome_oscillator(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate the Awesome Oscillator (AO).

    AO = SMA(median_price, 5) - SMA(median_price, 34)

    Returns a copy of df with added column: ao
    """
    median = (df["high"] + df["low"]) / 2.0
    out = df.copy()
    out["ao"] = median.rolling(window=5).mean() - median.rolling(window=34).mean()
    return out


# ─── Fractais ─────────────────────────────────────────────────────────────────


def fractals(df: pd.DataFrame) -> pd.DataFrame:
    """Detect Bill Williams Fractals (5-bar pattern).

    Bearish fractal (resistance): bar[i] has the HIGHEST high among
        bar[i-2], bar[i-1], bar[i], bar[i+1], bar[i+2].

    Bullish fractal (support): bar[i] has the LOWEST low among
        bar[i-2], bar[i-1], bar[i], bar[i+1], bar[i+2].

    Returns a copy of df with added columns:
        fractal_high  — price of bearish fractal (NaN if not a fractal)
        fractal_low   — price of bullish fractal (NaN if not a fractal)

    Note: The most recent 2 bars can never be fractals (require future bars).
    """
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)
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

    out = df.copy()
    out["fractal_high"] = fractal_high
    out["fractal_low"] = fractal_low
    return out


# ─── Pipeline completo ────────────────────────────────────────────────────────


def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all indicators to a OHLCV DataFrame in one call.

    Requires at minimum 200 candles for reliable SMMA convergence.
    The last candle (index -1) is typically incomplete and should be
    excluded from signal evaluation by the caller.
    """
    out = alligator(df)
    out = awesome_oscillator(out)
    out = fractals(out)
    return out


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
