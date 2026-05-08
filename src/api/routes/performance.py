"""Rota REST para consulta de métricas de performance de trades (RF-11)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.api.datetime_utils import BRAZIL_TIMEZONE, to_brazil_datetime_str, to_iso8601_utc

router = APIRouter()


@router.get("/performance")
async def get_performance(request: Request) -> JSONResponse:
    """Retorna métricas de performance agregadas sobre trades fechados.

    Métricas calculadas sobre trades com status CLOSED_TP, CLOSED_SL ou CLOSED_MANUAL
    que possuem pnl_usdt preenchido.
    """
    try:
        repo = getattr(request.app.state, "repository", None)
        if repo is None:
            return JSONResponse(
                status_code=503,
                content={"error": "database_unavailable"},
            )
        metrics = await repo.get_performance_metrics()
        generated_at = to_iso8601_utc(datetime.now(UTC))
        metrics["generated_at"] = generated_at
        metrics["generated_at_br"] = to_brazil_datetime_str(generated_at)
        metrics["timezone"] = BRAZIL_TIMEZONE
        return JSONResponse(status_code=200, content=metrics)
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"error": "database_unavailable"},
        )


@router.get("/performance/by-symbol")
async def get_performance_by_symbol(request: Request) -> JSONResponse:
    """Retorna métricas RF-11 agrupadas por símbolo (SPEC_009)."""
    try:
        repo = getattr(request.app.state, "repository", None)
        if repo is None:
            return JSONResponse(status_code=503, content={"error": "database_unavailable"})
        by_symbol = await repo.get_performance_by_symbol()
        generated_at = to_iso8601_utc(datetime.now(UTC))
        return JSONResponse(
            status_code=200,
            content={
                "by_symbol": by_symbol,
                "generated_at": generated_at,
                "generated_at_br": to_brazil_datetime_str(generated_at),
                "timezone": BRAZIL_TIMEZONE,
            },
        )
    except Exception:
        return JSONResponse(status_code=503, content={"error": "database_unavailable"})


@router.get("/performance/by-timeframe")
async def get_performance_by_timeframe(request: Request) -> JSONResponse:
    """Retorna métricas RF-11 agrupadas por timeframe (SPEC_009)."""
    try:
        repo = getattr(request.app.state, "repository", None)
        if repo is None:
            return JSONResponse(status_code=503, content={"error": "database_unavailable"})
        by_timeframe = await repo.get_performance_by_timeframe()
        generated_at = to_iso8601_utc(datetime.now(UTC))
        return JSONResponse(
            status_code=200,
            content={
                "by_timeframe": by_timeframe,
                "generated_at": generated_at,
                "generated_at_br": to_brazil_datetime_str(generated_at),
                "timezone": BRAZIL_TIMEZONE,
            },
        )
    except Exception:
        return JSONResponse(status_code=503, content={"error": "database_unavailable"})
