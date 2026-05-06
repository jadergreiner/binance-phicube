"""Rota de health check para monitoramento operacional da API."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
async def health_check(request: Request) -> JSONResponse:
    """Verifica saúde da API e conectividade com MongoDB.

    Retorna 200 quando MongoDB responde, 503 caso contrário.
    bot_process sempre "unknown" — bot e API são processos independentes.
    """
    repo = getattr(request.app.state, "repository", None)
    if repo is None:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "mongodb": "error",
                "bot_process": "unknown",
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            },
        )

    try:
        await repo.database.command("ping")
        mongodb_status = "ok"
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "mongodb": "error",
                "bot_process": "unknown",
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "mongodb": mongodb_status,
            "bot_process": "unknown",
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        },
    )
