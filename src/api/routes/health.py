"""Rota de health check para monitoramento operacional da API."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.api.datetime_utils import BRAZIL_TIMEZONE, to_brazil_datetime_str, to_iso8601_utc
from src.monitoring.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)
_INACTIVITY_THRESHOLD_MINUTES = 10
_BOT_HEARTBEAT_THRESHOLD_MINUTES = 10


async def _get_bot_process_status(repo) -> tuple[str, str | None]:
    """Deriva bot_process e last_heartbeat_at do último heartbeat na collection audit.

    Retorna: (status, last_heartbeat_at_iso)
    status: "alive" | "dead" | "unknown"
    """
    try:
        last_heartbeat_at = await repo.get_last_heartbeat_at()
    except Exception:
        return "unknown", None

    if last_heartbeat_at is None:
        return "dead", None

    delta_minutes = (datetime.now(UTC) - last_heartbeat_at).total_seconds() / 60
    status = "alive" if delta_minutes <= _BOT_HEARTBEAT_THRESHOLD_MINUTES else "dead"
    return status, to_iso8601_utc(last_heartbeat_at)


@router.get("/health")
@router.get("/system/health")
async def health_check(request: Request) -> JSONResponse:
    """Verifica saúde da API, MongoDB e processo bot via heartbeat (SPEC_017).

    Retorna 200 quando MongoDB responde, 503 caso contrário.
    bot_process derivado do último heartbeat na collection audit.
    """
    repo = getattr(request.app.state, "repository", None)
    if repo is None:
        timestamp = to_iso8601_utc(datetime.now(UTC))
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "mongodb": "error",
                "bot_process": "unknown",
                "last_heartbeat_at": None,
                "last_heartbeat_at_br": None,
                "timestamp": timestamp,
                "timestamp_br": to_brazil_datetime_str(timestamp),
                "timezone": BRAZIL_TIMEZONE,
            },
        )

    try:
        await repo.database.command("ping")
        mongodb_status = "ok"
    except Exception:
        timestamp = to_iso8601_utc(datetime.now(UTC))
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "mongodb": "error",
                "bot_process": "unknown",
                "last_heartbeat_at": None,
                "last_heartbeat_at_br": None,
                "timestamp": timestamp,
                "timestamp_br": to_brazil_datetime_str(timestamp),
                "timezone": BRAZIL_TIMEZONE,
            },
        )

    bot_process, last_heartbeat_at = await _get_bot_process_status(repo)
    timestamp = to_iso8601_utc(datetime.now(UTC))

    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "mongodb": mongodb_status,
            "bot_process": bot_process,
            "last_heartbeat_at": last_heartbeat_at,
            "last_heartbeat_at_br": to_brazil_datetime_str(last_heartbeat_at),
            "timestamp": timestamp,
            "timestamp_br": to_brazil_datetime_str(timestamp),
            "timezone": BRAZIL_TIMEZONE,
        },
    )


@router.get("/bot-activity")
async def get_bot_activity(request: Request) -> JSONResponse:
    """Expõe atividade recente do bot com degradação silenciosa."""
    checked_at = datetime.now(UTC)
    checked_at_iso = to_iso8601_utc(checked_at)
    repo = getattr(request.app.state, "repository", None)

    if repo is None:
        return JSONResponse(
            status_code=200,
            content={
                "status": "inactive",
                "last_activity_at": None,
                "last_activity_at_br": None,
                "minutes_since_last_activity": None,
                "threshold_minutes": _INACTIVITY_THRESHOLD_MINUTES,
                "checked_at": checked_at_iso,
                "checked_at_br": to_brazil_datetime_str(checked_at_iso),
                "timezone": BRAZIL_TIMEZONE,
            },
        )

    try:
        last_activity_at = await repo.get_last_bot_activity_at()
    except Exception as exc:
        logger.warning("dashboard_bot_activity_check_failed", error_type=type(exc).__name__)
        last_activity_at = None

    if last_activity_at is None:
        return JSONResponse(
            status_code=200,
            content={
                "status": "inactive",
                "last_activity_at": None,
                "last_activity_at_br": None,
                "minutes_since_last_activity": None,
                "threshold_minutes": _INACTIVITY_THRESHOLD_MINUTES,
                "checked_at": checked_at_iso,
                "checked_at_br": to_brazil_datetime_str(checked_at_iso),
                "timezone": BRAZIL_TIMEZONE,
            },
        )

    minutes_since_last_activity = max(
        0.0, round((checked_at - last_activity_at).total_seconds() / 60, 1)
    )
    status = (
        "active" if minutes_since_last_activity <= _INACTIVITY_THRESHOLD_MINUTES else "inactive"
    )
    return JSONResponse(
        status_code=200,
        content={
            "status": status,
            "last_activity_at": to_iso8601_utc(last_activity_at),
            "last_activity_at_br": to_brazil_datetime_str(last_activity_at),
            "minutes_since_last_activity": minutes_since_last_activity,
            "threshold_minutes": _INACTIVITY_THRESHOLD_MINUTES,
            "checked_at": checked_at_iso,
            "checked_at_br": to_brazil_datetime_str(checked_at_iso),
            "timezone": BRAZIL_TIMEZONE,
        },
    )
