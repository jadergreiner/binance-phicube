"""Rota de health check para monitoramento operacional da API."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.api.datetime_utils import BRAZIL_TIMEZONE, to_brazil_datetime_str, to_iso8601_utc
from src.monitoring.logger import get_logger
from src.resilience import CircuitBreakerState

if TYPE_CHECKING:
    from src.exchange.resilient_binance_client import ResilientBinanceClient
    from src.storage.resilient_repository import ResilientMongoRepository

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


def _get_circuit_breaker_summary(
    resilient_client: ResilientBinanceClient | None = None,
    resilient_repo: ResilientMongoRepository | None = None,
) -> tuple[dict[str, dict[str, str]], str]:
    """
    Extrai sumários de circuit breakers de cliente Binance e MongoDB.

    Args:
        resilient_client: ResilientBinanceClient (opcional)
        resilient_repo: ResilientMongoRepository (opcional)

    Returns:
        (circuit_breakers_dict, overall_status)
        circuit_breakers_dict: {'binance': {...}, 'mongodb': {...}}
        overall_status: 'healthy' | 'degraded' | 'critical'
    """
    circuit_breakers: dict[str, dict[str, str]] = {}
    all_states: list[str] = []

    # Extrai states do cliente Binance
    if resilient_client is not None:
        try:
            binance_cb_summary = resilient_client.registry.state_summary()
            circuit_breakers["binance"] = binance_cb_summary
            all_states.extend(binance_cb_summary.values())
        except Exception as exc:
            logger.warning(
                "health_check_binance_cb_extraction_failed",
                error=type(exc).__name__,
            )
            circuit_breakers["binance"] = {}

    # Extrai states do MongoDB
    if resilient_repo is not None:
        try:
            mongodb_cb_summary = resilient_repo.registry.state_summary()
            circuit_breakers["mongodb"] = mongodb_cb_summary
            all_states.extend(mongodb_cb_summary.values())
        except Exception as exc:
            logger.warning(
                "health_check_mongodb_cb_extraction_failed",
                error=type(exc).__name__,
            )
            circuit_breakers["mongodb"] = {}

    # Determina overall status
    # Verifica se há Tipo A (critical) aberto
    type_a_open_patterns = ["create_order", "create_stop_loss", "fetch_positions"]
    has_type_a_open = any(
        state == CircuitBreakerState.OPEN.value
        for cb_dict in circuit_breakers.values()
        for name, state in cb_dict.items()
        if any(pattern in name for pattern in type_a_open_patterns)
    )

    if has_type_a_open:
        overall_status = "critical"
    elif any(state == CircuitBreakerState.OPEN.value for state in all_states):
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return circuit_breakers, overall_status


@router.get("/health")
@router.get("/system/health")
async def health_check(request: Request) -> JSONResponse:
    """Verifica saúde da API, MongoDB, processo bot e circuit breakers (SPEC_017, SPEC_034).

    Retorna:
    - 200: Saúde geral OK (MongoDB up, process heartbeat, circuit breakers coletados)
    - 503: MongoDB down ou repositório indisponível

    Inclui sumário de circuit breakers por namespace (binance, mongodb).
    Status geral: 'healthy' (todos CLOSED) | 'degraded' (algum OPEN, sem Tipo A)
               | 'critical' (Tipo A aberto) | 'error' (MongoDB ou repo fora)
    """
    repo = getattr(request.app.state, "repository", None)
    resilient_client = getattr(request.app.state, "resilient_client", None)
    resilient_repo = getattr(request.app.state, "resilient_repo", None)

    timestamp = to_iso8601_utc(datetime.now(UTC))
    timestamp_br = to_brazil_datetime_str(timestamp)

    # Se repositório não disponível, retorna erro
    if repo is None:
        circuit_breakers, cb_status = _get_circuit_breaker_summary(resilient_client, resilient_repo)
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "mongodb": "error",
                "bot_process": "unknown",
                "last_heartbeat_at": None,
                "last_heartbeat_at_br": None,
                "circuit_breakers": circuit_breakers,
                "circuit_breaker_status": cb_status,
                "timestamp": timestamp,
                "timestamp_br": timestamp_br,
                "timezone": BRAZIL_TIMEZONE,
            },
        )

    # Tenta ping no MongoDB
    try:
        await repo.database.command("ping")
        mongodb_status = "ok"
    except Exception as exc:
        logger.warning(
            "health_check_mongodb_ping_failed",
            error=type(exc).__name__,
        )
        circuit_breakers, cb_status = _get_circuit_breaker_summary(resilient_client, resilient_repo)
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "mongodb": "error",
                "bot_process": "unknown",
                "last_heartbeat_at": None,
                "last_heartbeat_at_br": None,
                "circuit_breakers": circuit_breakers,
                "circuit_breaker_status": cb_status,
                "timestamp": timestamp,
                "timestamp_br": timestamp_br,
                "timezone": BRAZIL_TIMEZONE,
            },
        )

    # MongoDB OK, obtém bot process status
    bot_process, last_heartbeat_at = await _get_bot_process_status(repo)

    # Extrai sumários de circuit breakers (robusto — nunca levanta exception)
    circuit_breakers, cb_status = _get_circuit_breaker_summary(resilient_client, resilient_repo)

    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "mongodb": mongodb_status,
            "bot_process": bot_process,
            "last_heartbeat_at": last_heartbeat_at,
            "last_heartbeat_at_br": to_brazil_datetime_str(last_heartbeat_at),
            "circuit_breakers": circuit_breakers,
            "circuit_breaker_status": cb_status,
            "timestamp": timestamp,
            "timestamp_br": timestamp_br,
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
