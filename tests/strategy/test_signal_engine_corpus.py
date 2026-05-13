"""
Suite de validacao da SPEC_013 — conformidade do SignalEngine com o corpus.

Cada caso do corpus eh um teste parametrizado individual.
O corpus em docs/corpus/signal_corpus_v1.json deve existir antes de rodar.
Se ausente, a suite e pulada graciosamente (nao falha no CI).

Execucao:
    pytest tests/strategy/test_signal_engine_corpus.py -v
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import pytest
from pydantic import BaseModel, field_validator

from src.strategies.williams_strategy import WilliamsStrategy
from src.strategy.indicators import compute_all_optimized
from src.strategy.plugin_base import SignalResult
from src.strategy.plugin_registry import PluginRegistry
from src.strategy.signal_engine import SignalEngine

CORPUS_PATH = Path("docs/corpus/signal_corpus_v1.json")

_REGISTRY = PluginRegistry(plugin_timeout=30.0)
_REGISTRY.register("williams", WilliamsStrategy(risk_reward_ratio=2.0))
_ENGINE = SignalEngine(plugin_registry=_REGISTRY, risk_reward_ratio=2.0)


# ─── Schema Pydantic do corpus (RNF-003) ─────────────────────────────────────


class _FractalRef(BaseModel):
    type: Literal["high", "low"]
    price: float
    bar_index: int


class _AlligatorState(BaseModel):
    jaw: float | None = None
    teeth: float | None = None
    lips: float | None = None
    jaw_above_teeth: bool
    teeth_above_lips: bool
    lips_direction: str
    description: str = ""


class _AoValue(BaseModel):
    current: float
    prev: float
    crossing_zero: bool
    histogram_color: Literal["green", "red"]


class _ConditionsMet(BaseModel):
    alligator_bullish: bool
    ao_positive: bool
    close_above_fractal_high: bool
    valid_sl_fractal_low: bool


class CorpusCase(BaseModel):
    case_id: str
    symbol: str
    timeframe: str
    date: str
    direction: Literal["long", "short"]
    fractal_ref: _FractalRef
    alligator_state: _AlligatorState
    ao_value: _AoValue
    close: float
    conditions_met: _ConditionsMet
    expected_signal: Literal["long", "short"] | None
    notes: str = ""
    ohlcv_snapshot: list[list] | None = None

    @field_validator("case_id")
    @classmethod
    def case_id_nao_vazio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("case_id não pode ser vazio")
        return v


# ─── Carregamento do corpus ───────────────────────────────────────────────────


def _load_corpus() -> list[dict[str, Any]]:
    if not CORPUS_PATH.exists():
        return []
    raw = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    # Valida schema de cada caso — levanta ValidationError se estrutura for inválida
    for item in raw:
        CorpusCase.model_validate(item)
    return raw


def _corpus_params() -> list[tuple[str, dict]]:
    return [(c["case_id"], c) for c in _load_corpus()]


# ─── Reconstrucao de DataFrame a partir de ohlcv_snapshot ────────────────────


def _reconstruct_df(ohlcv_snapshot: list[list]) -> pd.DataFrame:
    """Reconstroi DataFrame padronizado a partir do snapshot armazenado no corpus.

    Formato do snapshot: [[open_time_ms, open, high, low, close, volume], ...]
    """
    df = pd.DataFrame(
        ohlcv_snapshot,
        columns=["open_time", "open", "high", "low", "close", "volume"],
    )
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
    return df.reset_index(drop=True)


# ─── Testes parametrizados ────────────────────────────────────────────────────

_PARAMS = _corpus_params()


@pytest.mark.skipif(not CORPUS_PATH.exists(), reason=f"Corpus ausente: {CORPUS_PATH}")
@pytest.mark.parametrize(
    "case_id,case",
    _PARAMS,
    ids=[p[0] for p in _PARAMS] if _PARAMS else [],
)
async def test_signal_engine_conforma_corpus(case_id: str, case: dict) -> None:
    """Valida que SignalEngine produz o sinal esperado para cada caso do corpus."""
    if "ohlcv_snapshot" not in case:
        pytest.skip(f"{case_id}: sem ohlcv_snapshot — regenere com --generate-v1")

    df = _reconstruct_df(case["ohlcv_snapshot"])

    if len(df) < 50:
        pytest.skip(f"{case_id}: snapshot com {len(df)} candles — insuficiente")

    enriched = compute_all_optimized(df)
    result_obj = await _ENGINE.evaluate(case["symbol"], case["timeframe"], enriched)
    assert result_obj.is_ok()
    signal = result_obj.unwrap()
    expected = case["expected_signal"]

    if not isinstance(signal, SignalResult):
        obtained = None
    else:
        obtained = signal.direction.lower()

    if expected is None:
        assert not isinstance(signal, SignalResult), (
            f"{case_id} [{case['symbol']} {case['timeframe']} {case['date']}]: "
            f"esperado None, obtido {obtained}"
        )
    elif expected.upper() == "LONG":
        assert isinstance(signal, SignalResult) and signal.direction == "LONG", (
            f"{case_id} [{case['symbol']} {case['timeframe']} {case['date']}]: "
            f"esperado LONG, obtido {obtained}"
        )
    elif expected.upper() == "SHORT":
        assert isinstance(signal, SignalResult) and signal.direction == "SHORT", (
            f"{case_id} [{case['symbol']} {case['timeframe']} {case['date']}]: "
            f"esperado SHORT, obtido {obtained}"
        )
    else:
        pytest.fail(f"{case_id}: expected_signal invalido: {expected!r}")


# ─── Relatorio de conformidade ────────────────────────────────────────────────


def pytest_terminal_summary(terminalreporter: Any, exitstatus: int, config: Any) -> None:  # noqa: ARG001
    """Imprime relatorio de conformidade ao final da suite."""
    corpus = _load_corpus()
    if not corpus:
        return

    passed = terminalreporter.stats.get("passed", [])
    failed = terminalreporter.stats.get("failed", [])

    corpus_passed = [r for r in passed if "test_signal_engine_conforma_corpus" in r.nodeid]
    corpus_failed = [r for r in failed if "test_signal_engine_conforma_corpus" in r.nodeid]

    total = len(corpus_passed) + len(corpus_failed)
    if total == 0:
        return

    taxa = 100.0 * len(corpus_passed) / total
    terminalreporter.write_sep("=", "Relatorio de Conformidade SPEC_013")
    terminalreporter.write_line(f"Total casos : {total}")
    terminalreporter.write_line(f"Passados    : {len(corpus_passed)} ({taxa:.1f}%)")
    terminalreporter.write_line(f"Falhos      : {len(corpus_failed)}")
    if corpus_failed:
        terminalreporter.write_line("\nCasos divergentes (engine vs corpus):")
        for r in corpus_failed:
            terminalreporter.write_line(f"  {r.nodeid}")
    terminalreporter.write_sep("=", "")
