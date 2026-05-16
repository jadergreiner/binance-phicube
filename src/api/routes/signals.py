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
