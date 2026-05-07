"""Rotas de trades para visibilidade operacional do dashboard."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


def _to_iso8601(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _normalize_trade(trade: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(trade)
    for key in ("opened_at", "closed_at"):
        value = normalized.get(key)
        if isinstance(value, datetime):
            normalized[key] = _to_iso8601(value)
    return normalized


@router.get("/trades/history")
async def get_trade_history(request: Request) -> JSONResponse:
    """Retorna os últimos 50 trades fechados."""
    repo = getattr(request.app.state, "repository", None)
    if repo is None:
        return JSONResponse(status_code=503, content={"detail": "Repositório indisponível"})

    try:
        trades = await repo.get_trade_history(limit=50)
    except Exception:
        return JSONResponse(status_code=503, content={"detail": "Repositório indisponível"})

    normalized_trades = [_normalize_trade(trade) for trade in trades]
    return JSONResponse(
        status_code=200,
        content={
            "trades": normalized_trades,
            "total": len(normalized_trades),
            "generated_at": _to_iso8601(datetime.now(UTC)),
        },
    )
