"""Rotas de sinais para visibilidade operacional do dashboard."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from src.api.datetime_utils import (
    BRAZIL_TIMEZONE,
    enrich_datetime_fields,
    to_brazil_datetime_str,
    to_iso8601_utc,
)

router = APIRouter()

# Timeframe em milissegundos para buscar candles posteriores ao sinal
_TF_MS = {
    "1m": 60_000,
    "3m": 180_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}
# Máximo de candles para verificar após o sinal (≈ 3 dias em 15m = 288 velas)
_MAX_CANDLES = 288


def _classify_signal(
    signal: dict[str, Any],
    candles: list[list],
) -> dict[str, Any]:
    """Classifica um sinal como TP_HIT, SL_HIT ou OPEN com base nos candles posteriores."""
    direction = str(signal.get("direction", "")).upper()
    entry = float(signal["entry_price"])
    sl = float(signal["stop_loss"])
    tp = float(signal["take_profit"])

    outcome = "OPEN"
    outcome_price: float | None = None
    outcome_at: datetime | None = None

    for candle in candles:
        # candle: [timestamp_ms, open, high, low, close, volume]
        high = float(candle[2])
        low = float(candle[3])
        ts = datetime.fromtimestamp(candle[0] / 1000, tz=UTC)

        if direction == "LONG":
            # SL primeiro (low toca SL antes do high tocar TP na mesma vela)
            if low <= sl:
                outcome = "SL_HIT"
                outcome_price = sl
                outcome_at = ts
                break
            if high >= tp:
                outcome = "TP_HIT"
                outcome_price = tp
                outcome_at = ts
                break
        elif direction == "SHORT":
            if high >= sl:
                outcome = "SL_HIT"
                outcome_price = sl
                outcome_at = ts
                break
            if low <= tp:
                outcome = "TP_HIT"
                outcome_price = tp
                outcome_at = ts
                break

    pnl_pct: float | None = None
    if outcome != "OPEN" and outcome_price is not None:
        if direction == "LONG":
            pnl_pct = round((outcome_price - entry) / entry * 100, 3)
        elif direction == "SHORT":
            pnl_pct = round((entry - outcome_price) / entry * 100, 3)

    return {
        "outcome": outcome,
        "outcome_price": outcome_price,
        "outcome_at": outcome_at,
        "pnl_pct": pnl_pct,
        "candles_checked": len(candles),
    }

_LEGACY_STATUS = "UNKNOWN_LEGACY"
_LEGACY_REASON = "causa indisponível (pré-rastreio)"


def _normalize_signal(signal: dict[str, Any]) -> dict[str, Any]:
    normalized = enrich_datetime_fields(signal, ("detected_at", "outcome_at"))

    if not normalized.get("execution_status"):
        normalized["execution_status"] = _LEGACY_STATUS
        if not normalized.get("execution_reason"):
            normalized["execution_reason"] = _LEGACY_REASON

    return normalized


@router.get("/signals/history")
async def get_signal_history(request: Request) -> JSONResponse:
    """Retorna os últimos 50 sinais detectados com desfecho de execução."""
    repo = getattr(request.app.state, "repository", None)
    if repo is None:
        return JSONResponse(status_code=503, content={"detail": "Repositório indisponível"})

    try:
        signals = await repo.get_signal_history(limit=50)
    except Exception:
        return JSONResponse(status_code=503, content={"detail": "Repositório indisponível"})

    normalized_signals = [_normalize_signal(signal) for signal in signals]
    generated_at = to_iso8601_utc(datetime.now(UTC))
    return JSONResponse(
        status_code=200,
        content={
            "signals": normalized_signals,
            "total": len(normalized_signals),
            "generated_at": generated_at,
            "generated_at_br": to_brazil_datetime_str(generated_at),
            "timezone": BRAZIL_TIMEZONE,
        },
    )


@router.get("/signals/diagnosis/{symbol}/{timeframe}")
async def get_signal_generation_diagnosis(
    request: Request,
    symbol: str,
    timeframe: str,
) -> JSONResponse:
    """Retorna diagnóstico consolidado da geração de sinais por símbolo/timeframe."""
    repo = getattr(request.app.state, "repository", None)
    if repo is None:
        return JSONResponse(status_code=503, content={"detail": "Repositório indisponível"})

    try:
        diagnosis = await repo.get_signal_generation_diagnosis(
            symbol=symbol.upper(),
            timeframe=timeframe,
        )
    except Exception:
        return JSONResponse(status_code=503, content={"detail": "Repositório indisponível"})

    payload = enrich_datetime_fields(
        diagnosis,
        ("last_evidence_at",),
    )
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@router.get("/signals/advisory-performance")
async def get_advisory_performance(request: Request) -> JSONResponse:
    """Retorna taxa de acerto dos sinais advisory já classificados por backtest."""
    repo = getattr(request.app.state, "repository", None)
    if repo is None:
        return JSONResponse(status_code=503, content={"detail": "Repositório indisponível"})

    try:
        signals = await repo.get_signal_history(limit=500)
    except Exception:
        return JSONResponse(status_code=503, content={"detail": "Repositório indisponível"})

    classified = [s for s in signals if s.get("backtest_outcome")]
    tp_hits = [s for s in classified if s["backtest_outcome"] == "TP_HIT"]
    sl_hits = [s for s in classified if s["backtest_outcome"] == "SL_HIT"]
    open_signals = [s for s in classified if s["backtest_outcome"] == "OPEN"]
    pending = [s for s in signals if not s.get("backtest_outcome")]

    win_rate = round(len(tp_hits) / len(classified) * 100, 1) if classified else None
    avg_pnl_pct = None
    pnl_values = [
        s.get("backtest_pnl_pct") for s in classified if s.get("backtest_pnl_pct") is not None
    ]
    if pnl_values:
        avg_pnl_pct = round(sum(pnl_values) / len(pnl_values), 3)

    generated_at = to_iso8601_utc(datetime.now(UTC))
    return JSONResponse(
        status_code=200,
        content={
            "summary": {
                "total_classified": len(classified),
                "tp_hits": len(tp_hits),
                "sl_hits": len(sl_hits),
                "open": len(open_signals),
                "pending_backtest": len(pending),
                "win_rate_pct": win_rate,
                "avg_pnl_pct": avg_pnl_pct,
            },
            "signals": [_normalize_signal(s) for s in classified],
            "generated_at": generated_at,
            "generated_at_br": to_brazil_datetime_str(generated_at),
            "timezone": BRAZIL_TIMEZONE,
        },
    )


@router.post("/signals/advisory-backtest")
async def run_advisory_backtest(request: Request) -> JSONResponse:
    """Classifica sinais advisory pendentes buscando candles Binance posteriores.

    Para cada sinal sem backtest_outcome:
    - Busca candles do timeframe a partir de detected_at
    - Classifica como TP_HIT, SL_HIT ou OPEN (se nenhum nível foi tocado ainda)
    - Persiste resultado no BD via backtest_outcome
    """
    repo = getattr(request.app.state, "repository", None)
    if repo is None:
        return JSONResponse(status_code=503, content={"detail": "Repositório indisponível"})

    client = getattr(request.app.state, "dashboard_client", None)
    if client is None:
        return JSONResponse(status_code=503, content={"detail": "Cliente Binance indisponível"})

    try:
        pending = await repo.get_advisory_signals(limit=200)
    except Exception:
        return JSONResponse(status_code=503, content={"detail": "Repositório indisponível"})

    if not pending:
        return JSONResponse(status_code=200, content={"classified": 0, "results": []})

    results = []
    for signal in pending:
        signal_id = signal.get("_id")
        symbol = signal.get("symbol", "")
        timeframe = str(signal.get("timeframe", "15m"))
        detected_at = signal.get("detected_at")

        if not signal_id or not symbol or detected_at is None:
            continue

        # Normalizar símbolo para CCXT (BTCUSDT → BTC/USDT:USDT)
        raw = symbol.replace("/USDT:USDT", "").replace("USDT", "")
        ccxt_symbol = f"{raw}/USDT:USDT"

        since_ms = (
            int(detected_at.timestamp() * 1000) if hasattr(detected_at, "timestamp") else None
        )
        if since_ms is None:
            continue

        tf_ms = _TF_MS.get(timeframe, 900_000)
        # Avançar 1 candle após o sinal (não incluir a vela do próprio sinal)
        since_ms = since_ms + tf_ms

        try:
            candles = await client._exchange.fetch_ohlcv(
                ccxt_symbol, timeframe, since=since_ms, limit=_MAX_CANDLES
            )
        except Exception:
            continue

        classification = _classify_signal(signal, candles)
        outcome = classification["outcome"]

        try:
            await repo.set_signal_backtest_outcome(
                signal_id,
                outcome=outcome,
                outcome_price=classification["outcome_price"],
                outcome_at=classification["outcome_at"],
                candles_checked=classification["candles_checked"],
            )
        except Exception:
            continue

        results.append({
            "signal_id": signal_id,
            "symbol": symbol,
            "direction": signal.get("direction"),
            "entry_price": signal.get("entry_price"),
            "stop_loss": signal.get("stop_loss"),
            "take_profit": signal.get("take_profit"),
            "detected_at": (
                to_iso8601_utc(detected_at)
                if hasattr(detected_at, "isoformat")
                else str(detected_at)
            ),
            "outcome": outcome,
            "outcome_price": classification["outcome_price"],
            "pnl_pct": classification["pnl_pct"],
            "candles_checked": classification["candles_checked"],
        })

    tp = sum(1 for r in results if r["outcome"] == "TP_HIT")
    sl = sum(1 for r in results if r["outcome"] == "SL_HIT")
    open_count = sum(1 for r in results if r["outcome"] == "OPEN")
    win_rate = round(tp / (tp + sl) * 100, 1) if (tp + sl) > 0 else None

    return JSONResponse(
        status_code=200,
        content={
            "classified": len(results),
            "tp_hits": tp,
            "sl_hits": sl,
            "open": open_count,
            "win_rate_pct": win_rate,
            "results": results,
        },
    )
