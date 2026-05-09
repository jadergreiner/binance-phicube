"""Rotas REST para onboarding de novos símbolos (SPEC_019)."""

from __future__ import annotations

import asyncio
import dataclasses
import math
import os
import re
from asyncio import Semaphore
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

import pandas as pd
from bson import ObjectId
from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

from src.monitoring.logger import get_logger
from src.strategy.indicators import compute_all, last_valid_fractal_high, last_valid_fractal_low
from src.strategy.signal_engine import SignalEngine

router = APIRouter(prefix="/onboarding", tags=["onboarding"])
logger = get_logger(__name__)

_VALID_TIMEFRAMES = {"1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"}
_SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,15}USDT$")
_COMMODITIES = frozenset({"XPTUSDT", "COPPERUSDT"})
_MARKET_ANALYSIS_CANDLES_LIMIT = 260
_CONSISTENCY_STATUS_CONSISTENT = "CONSISTENT"
_CONSISTENCY_STATUS_DEGRADED = "DEGRADED"


def _is_write_authorized(request: Request) -> bool:
    settings = request.app.state.settings
    if not getattr(settings, "dashboard_write_auth_required", False):
        logger.info("dashboard_write_auth_granted", reason="bypass_disabled")
        return True

    expected_token = getattr(settings, "dashboard_write_auth_token", None)
    auth_header = request.headers.get("Authorization", "")
    expected_header = f"Bearer {expected_token}" if expected_token else ""
    authorized = bool(expected_header) and auth_header == expected_header
    if authorized:
        logger.info("dashboard_write_auth_granted", reason="valid_bearer")
        return True

    logger.warning("dashboard_write_auth_denied", reason="invalid_or_missing_bearer")
    return False


def _unauthorized_response() -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"error": "unauthorized", "detalhe": "Bearer token invalido ou ausente"},
    )


def _serialize_session(doc: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in doc.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat().replace("+00:00", "Z")
        elif isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            out[k] = 0.0
        else:
            out[k] = v
    return out


def _serialize_backtest(result: Any) -> dict[str, Any] | None:
    if result is None:
        return None
    if dataclasses.is_dataclass(result) and not isinstance(result, type):
        d: dict[str, Any] = {}
        for f in dataclasses.fields(result):  # type: ignore[arg-type]
            v = getattr(result, f.name)
            if isinstance(v, datetime):
                d[f.name] = v.isoformat().replace("+00:00", "Z")
            elif isinstance(v, list):
                d[f.name] = []
            elif isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                d[f.name] = 0.0
            else:
                d[f.name] = v
        return d
    return result


def _active_symbols(request: Request) -> set[str]:
    try:
        settings = request.app.state.settings
        return {cfg.symbol for cfg in settings.symbol_timeframes}
    except Exception:
        return set()


def _compose_triplet(symbol: str, timeframe: str, leverage: int) -> str:
    return f"{symbol}:{timeframe}:{leverage}"


def _parse_triplet(triplet: str) -> tuple[str, str, int] | None:
    parts = [part.strip() for part in triplet.split(":")]
    if len(parts) != 3:
        return None
    symbol, timeframe, leverage_raw = parts
    if not symbol or not timeframe:
        return None
    try:
        leverage = int(leverage_raw)
    except (TypeError, ValueError):
        return None
    return symbol.upper(), timeframe, leverage


def _settings_triplets(request: Request) -> list[str]:
    settings = request.app.state.settings
    triplets: list[str] = []
    for cfg in getattr(settings, "symbol_timeframes", []):
        symbol = str(getattr(cfg, "symbol", "")).upper()
        timeframe = str(getattr(cfg, "timeframe", ""))
        leverage = int(getattr(cfg, "leverage", 0))
        if not symbol or not timeframe or leverage <= 0:
            continue
        triplets.append(_compose_triplet(symbol, timeframe, leverage))
    return triplets


def _approved_triplets(sessions: list[dict[str, Any]]) -> list[str]:
    approved: list[str] = []
    for session in sessions:
        if session.get("status") != "APPROVED":
            continue
        parsed = _parse_triplet(str(session.get("config_string") or ""))
        if parsed is None:
            continue
        symbol, timeframe, leverage = parsed
        approved.append(_compose_triplet(symbol, timeframe, leverage))
    return approved


def _merge_triplets(base_triplets: list[str], approved_triplets: list[str]) -> list[str]:
    merged: dict[tuple[str, str], int] = {}
    order: list[tuple[str, str]] = []

    def _upsert(triplet: str) -> None:
        parsed = _parse_triplet(triplet)
        if parsed is None:
            return
        symbol, timeframe, leverage = parsed
        key = (symbol, timeframe)
        if key not in merged:
            order.append(key)
        merged[key] = leverage

    for triplet in base_triplets:
        _upsert(triplet)
    for triplet in approved_triplets:
        _upsert(triplet)

    return [
        _compose_triplet(symbol, timeframe, merged[(symbol, timeframe)])
        for symbol, timeframe in order
    ]


def _resolve_env_path() -> Path:
    override = os.getenv("PHICUBE_ENV_PATH")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[3] / ".env"


def _upsert_env_key(path: Path, *, key: str, value: str) -> None:
    lines: list[str] = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()

    target_prefix = f"{key}="
    replaced = False
    for idx, line in enumerate(lines):
        if line.strip().startswith(target_prefix):
            lines[idx] = f"{target_prefix}{value}"
            replaced = True
            break

    if not replaced:
        lines.append(f"{target_prefix}{value}")

    content = "\n".join(lines).rstrip() + "\n"
    path.write_text(content, encoding="utf-8")


def _validate_symbol(symbol: str) -> JSONResponse | None:
    if not _SYMBOL_RE.match(symbol):
        return JSONResponse(
            status_code=422,
            content={
                "error": "symbol_invalido",
                "detalhe": "Formato esperado: [A-Z0-9]{2,15}USDT",
            },
        )
    return None


def _validate_timeframe(timeframe: str) -> JSONResponse | None:
    if timeframe not in _VALID_TIMEFRAMES:
        return JSONResponse(
            status_code=422,
            content={"error": "timeframe_invalido", "validos": sorted(_VALID_TIMEFRAMES)},
        )
    return None


def _parse_leverage(leverage_raw: Any) -> int | None:
    try:
        leverage = int(leverage_raw)
    except (TypeError, ValueError):
        return None
    if not (1 <= leverage <= 20):
        return None
    return leverage


def _validate_leverage(leverage_raw: Any) -> tuple[int | None, JSONResponse | None]:
    leverage = _parse_leverage(leverage_raw)
    if leverage is None:
        return None, JSONResponse(
            status_code=422,
            content={"error": "leverage_invalido", "detalhe": "Deve ser inteiro entre 1 e 20"},
        )
    return leverage, None


def _serialize_signal(signal: Any) -> dict[str, Any]:
    payload = signal.to_dict()
    detected_at = payload.get("detected_at")
    if isinstance(detected_at, datetime):
        payload["detected_at"] = detected_at.isoformat().replace("+00:00", "Z")
    return payload


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    return parsed


class _BacktestJobExecutor:
    def __init__(self, *, max_concurrency: int, timeout_seconds: int) -> None:
        self._semaphore = Semaphore(max(1, max_concurrency))
        self._timeout_seconds = max(5, timeout_seconds)

    async def run(self, run_fn) -> Any:
        async with self._semaphore:
            return await asyncio.wait_for(run_fn(), timeout=self._timeout_seconds)


def _job_error_response(code: str, message: str, *, status_code: int = 503) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error_code": code, "error_message": message},
    )


def _get_backtest_executor(request: Request) -> _BacktestJobExecutor:
    current = getattr(request.app.state, "backtest_job_executor", None)
    if current is not None:
        return current
    settings = request.app.state.settings
    max_concurrency = int(getattr(settings, "onboarding_backtest_job_max_concurrency", 2))
    timeout_seconds = int(getattr(settings, "onboarding_backtest_job_timeout_seconds", 600))
    executor = _BacktestJobExecutor(
        max_concurrency=max_concurrency,
        timeout_seconds=timeout_seconds,
    )
    request.app.state.backtest_job_executor = executor
    return executor


def _serialize_market_context(enriched: pd.DataFrame) -> dict[str, Any]:
    if enriched.empty:
        return {}
    last = enriched.iloc[-1]
    candle_open_time = last.get("open_time")
    candle_open_time_iso: str | None = None
    if hasattr(candle_open_time, "isoformat"):
        candle_open_time_iso = candle_open_time.isoformat().replace("+00:00", "Z")
    return {
        "candle_open_time": candle_open_time_iso,
        "open": _safe_float(last.get("open")),
        "high": _safe_float(last.get("high")),
        "low": _safe_float(last.get("low")),
        "close": _safe_float(last.get("close")),
        "volume": _safe_float(last.get("volume")),
        "jaw": _safe_float(last.get("jaw")),
        "teeth": _safe_float(last.get("teeth")),
        "lips": _safe_float(last.get("lips")),
        "ao": _safe_float(last.get("ao")),
        "fractal_high_recent": last_valid_fractal_high(enriched),
        "fractal_low_recent": last_valid_fractal_low(enriched),
    }


async def _build_symbol_timeframes_payload(request: Request) -> dict[str, Any]:
    repo = request.app.state.repository
    sessions = await repo.list_onboarding_sessions()
    merged_triplets = _merge_triplets(_settings_triplets(request), _approved_triplets(sessions))
    symbol_timeframes_line = ",".join(merged_triplets)
    env_path = _resolve_env_path()
    env_applied = False
    env_apply_error: str | None = None
    try:
        _upsert_env_key(env_path, key="SYMBOL_TIMEFRAMES", value=symbol_timeframes_line)
        env_applied = True
    except Exception as exc:
        env_apply_error = type(exc).__name__

    return {
        "symbol_timeframes_line": symbol_timeframes_line,
        "env_path": str(env_path),
        "env_applied": env_applied,
        "env_apply_error": env_apply_error,
        "operational_checklist": [
            "SYMBOL_TIMEFRAMES atualizado automaticamente no .env",
            "Reiniciar o bot para aplicar o novo simbolo",
            "Validar sessao via GET /onboarding e monitorar status/health no dashboard",
        ],
    }


def _read_env_key(path: Path, *, key: str) -> str | None:
    if not path.exists():
        return None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1]
    return None


def _build_sync_status(payload: dict[str, Any]) -> dict[str, Any]:
    env_applied = bool(payload.get("env_applied"))
    return {
        "env_applied": env_applied,
        "env_apply_error": payload.get("env_apply_error"),
        "symbol_timeframes_line": payload.get("symbol_timeframes_line", ""),
        "consistency_status": (
            _CONSISTENCY_STATUS_CONSISTENT if env_applied else _CONSISTENCY_STATUS_DEGRADED
        ),
    }


async def _apply_symbol_timeframes_sync(request: Request) -> dict[str, Any]:
    repo = request.app.state.repository
    payload = await _build_symbol_timeframes_payload(request)
    sync_status = _build_sync_status(payload)
    audit_payload = {
        "symbol_timeframes_line": payload.get("symbol_timeframes_line", ""),
        "env_path": payload.get("env_path"),
        "env_applied": payload.get("env_applied"),
        "env_apply_error": payload.get("env_apply_error"),
        "consistency_status": sync_status["consistency_status"],
    }
    event = (
        "onboarding_symbol_timeframes_sync_succeeded"
        if sync_status["consistency_status"] == _CONSISTENCY_STATUS_CONSISTENT
        else "onboarding_symbol_timeframes_sync_failed"
    )
    await repo.audit(event, audit_payload)
    payload["sync_status"] = sync_status
    return payload


async def _build_consistency_snapshot(request: Request) -> dict[str, Any]:
    repo = request.app.state.repository
    sessions = await repo.list_onboarding_sessions()
    approved_triplets = _approved_triplets(sessions)
    merged_triplets = _merge_triplets(_settings_triplets(request), approved_triplets)
    expected_line = ",".join(merged_triplets)
    env_path = _resolve_env_path()
    env_line = _read_env_key(env_path, key="SYMBOL_TIMEFRAMES")
    consistency_status = (
        _CONSISTENCY_STATUS_CONSISTENT
        if env_line == expected_line
        else _CONSISTENCY_STATUS_DEGRADED
    )
    return {
        "consistency_status": consistency_status,
        "expected_symbol_timeframes_line": expected_line,
        "env_symbol_timeframes_line": env_line or "",
        "env_path": str(env_path),
        "approved_sessions_total": sum(1 for s in sessions if s.get("status") == "APPROVED"),
        "approved_triplets_total": len(approved_triplets),
        "divergence_reason": (
            None
            if consistency_status == _CONSISTENCY_STATUS_CONSISTENT
            else "env_symbol_timeframes_mismatch"
        ),
    }


@router.get("")
async def list_sessions(request: Request) -> JSONResponse:
    repo = request.app.state.repository
    if repo is None:
        return JSONResponse(status_code=503, content={"error": "mongodb_unavailable"})
    sessions = await repo.list_onboarding_sessions()
    return JSONResponse(status_code=200, content=[_serialize_session(s) for s in sessions])


@router.get("/consistency")
async def get_consistency(request: Request) -> JSONResponse:
    repo = request.app.state.repository
    if repo is None:
        return JSONResponse(status_code=503, content={"error": "mongodb_unavailable"})
    snapshot = await _build_consistency_snapshot(request)
    return JSONResponse(status_code=200, content=snapshot)


@router.post("")
async def create_session(
    request: Request,
    body: Annotated[dict, Body()],
) -> JSONResponse:
    if not _is_write_authorized(request):
        return _unauthorized_response()

    repo = request.app.state.repository
    if repo is None:
        return JSONResponse(status_code=503, content={"error": "mongodb_unavailable"})

    symbol = str(body.get("symbol", "")).strip().upper()
    timeframe = str(body.get("timeframe", "")).strip()
    leverage_raw = body.get("leverage")

    symbol_error = _validate_symbol(symbol)
    if symbol_error is not None:
        return symbol_error
    timeframe_error = _validate_timeframe(timeframe)
    if timeframe_error is not None:
        return timeframe_error
    leverage, leverage_error = _validate_leverage(leverage_raw)
    if leverage_error is not None or leverage is None:
        return leverage_error

    # Símbolo já ativo?
    if symbol in _active_symbols(request):
        return JSONResponse(
            status_code=409,
            content={"error": "simbolo_ja_ativo", "symbol": symbol},
        )

    # Sessão já existe?
    existing = await repo.get_onboarding_session(symbol)
    if existing is not None:
        return JSONResponse(
            status_code=409,
            content={"error": "sessao_ja_existe", "symbol": symbol},
        )

    now = datetime.now(UTC)
    doc: dict[str, Any] = {
        "symbol": symbol,
        "timeframe": timeframe,
        "leverage": leverage,
        "status": "CANDIDATE",
        "created_at": now,
        "updated_at": now,
        "backtest_result": None,
        "backtest_limit": None,
        "backtest_error": None,
        "config_string": None,
        "notes": None,
    }
    await repo.create_onboarding_session(doc)
    return JSONResponse(status_code=201, content=_serialize_session(doc))


@router.get("/{symbol}")
async def get_session(request: Request, symbol: str) -> JSONResponse:
    repo = request.app.state.repository
    if repo is None:
        return JSONResponse(status_code=503, content={"error": "mongodb_unavailable"})
    session = await repo.get_onboarding_session(symbol.upper())
    if session is None:
        return JSONResponse(status_code=404, content={"error": "sessao_nao_encontrada"})
    return JSONResponse(status_code=200, content=_serialize_session(session))


@router.delete("/{symbol}")
async def delete_session(request: Request, symbol: str) -> JSONResponse:
    if not _is_write_authorized(request):
        return _unauthorized_response()

    repo = request.app.state.repository
    if repo is None:
        return JSONResponse(status_code=503, content={"error": "mongodb_unavailable"})
    sym = symbol.upper()
    session = await repo.get_onboarding_session(sym)
    if session is None:
        return JSONResponse(status_code=404, content={"error": "sessao_nao_encontrada"})
    was_approved = session.get("status") == "APPROVED"
    deleted = await repo.delete_onboarding_session(sym)
    if not deleted:
        return JSONResponse(status_code=404, content={"error": "sessao_nao_encontrada"})
    if not was_approved:
        return JSONResponse(status_code=204, content=None)
    sync_payload = await _apply_symbol_timeframes_sync(request)
    return JSONResponse(
        status_code=200,
        content={
            "deleted_symbol": sym,
            "sync_status": sync_payload["sync_status"],
            "symbol_timeframes_line": sync_payload["symbol_timeframes_line"],
            "env_path": sync_payload["env_path"],
            "env_applied": sync_payload["env_applied"],
            "env_apply_error": sync_payload["env_apply_error"],
            "operational_checklist": sync_payload["operational_checklist"],
        },
    )


@router.post("/{symbol}/backtest")
async def run_backtest(
    request: Request,
    symbol: str,
    body: Annotated[dict, Body()] = {},  # noqa: B006
) -> JSONResponse:
    """Endpoint legado síncrono desativado."""
    logger.warning(
        "onboarding_backtest_legacy_endpoint_used", endpoint="/onboarding/{symbol}/backtest"
    )
    if not _is_write_authorized(request):
        return _unauthorized_response()
    return JSONResponse(
        status_code=410,
        content={
            "error_code": "legacy_endpoint_deprecated",
            "error_message": "Endpoint legado desativado. Use o fluxo assíncrono por jobs.",
            "migration": {
                "create_job": f"/onboarding/{symbol.upper()}/backtest-jobs",
                "get_job": "/onboarding/backtest-jobs/{job_id}",
            },
        },
    )


async def _run_backtest_job(request: Request, job_id: str) -> None:
    repo = request.app.state.repository
    job = await repo.get_backtest_job(job_id)
    if job is None:
        return

    symbol = str(job.get("symbol") or "").upper()
    timeframe = str(job.get("timeframe") or "")
    limit = int(job.get("limit") or 35000)
    balance = float(job.get("initial_balance") or 1000.0)

    await repo.update_backtest_job(
        job_id,
        {"status": "running", "started_at": datetime.now(UTC)},
    )

    try:
        from src.backtest.engine import BacktestEngine
        from src.config.settings import get_settings
        from src.exchange.binance_client import BinanceClient

        settings = get_settings()
        client = BinanceClient(settings)
        await client.connect()
        try:
            engine = BacktestEngine(settings, client)
            result = await engine.run(
                symbol,
                timeframe,
                limit=limit,
                initial_balance=balance,
            )
        finally:
            await client.close()

        result_dict = _serialize_backtest(result)
        session = await repo.get_onboarding_session(symbol)
        if session is not None:
            next_status = "APPROVED" if session["status"] == "APPROVED" else "BACKTESTED"
            await repo.update_onboarding_session(
                symbol,
                {
                    "status": next_status,
                    "backtest_result": result_dict,
                    "backtest_limit": limit,
                    "backtest_error": None,
                },
            )

        await repo.update_backtest_job(
            job_id,
            {
                "status": "succeeded",
                "completed_at": datetime.now(UTC),
                "backtest_result": result_dict,
                "error_code": None,
                "error_message": None,
            },
        )
        logger.info("onboarding_backtest_job_succeeded", job_id=job_id, symbol=symbol)
    except TimeoutError:
        await repo.update_backtest_job(
            job_id,
            {
                "status": "failed",
                "completed_at": datetime.now(UTC),
                "error_code": "timeout",
                "error_message": "backtest job timed out",
            },
        )
        await repo.update_onboarding_session(symbol, {"backtest_error": "TimeoutError"})
        logger.warning("onboarding_backtest_job_timeout", job_id=job_id, symbol=symbol)
    except Exception as exc:
        error_code = type(exc).__name__.lower()
        await repo.update_backtest_job(
            job_id,
            {
                "status": "failed",
                "completed_at": datetime.now(UTC),
                "error_code": error_code,
                "error_message": str(exc)[:240] or type(exc).__name__,
            },
        )
        await repo.update_onboarding_session(symbol, {"backtest_error": type(exc).__name__})
        logger.warning(
            "onboarding_backtest_job_failed",
            job_id=job_id,
            symbol=symbol,
            error_type=type(exc).__name__,
        )


@router.post("/{symbol}/backtest-jobs")
async def create_backtest_job(
    request: Request,
    symbol: str,
    body: Annotated[dict, Body()] = {},  # noqa: B006
) -> JSONResponse:
    if not _is_write_authorized(request):
        return _unauthorized_response()

    repo = request.app.state.repository
    if repo is None:
        return _job_error_response(
            "mongodb_unavailable",
            "MongoDB indisponível",
            status_code=503,
        )

    sym = symbol.upper()
    session = await repo.get_onboarding_session(sym)
    if session is None:
        return _job_error_response(
            "sessao_nao_encontrada", "Sessão não encontrada", status_code=404
        )
    if session["status"] not in ("CANDIDATE", "BACKTESTED", "APPROVED"):
        return _job_error_response(
            "estado_invalido",
            f"Estado atual inválido: {session['status']}",
            status_code=409,
        )

    limit = int(body.get("limit", 35000))
    limit = max(50, min(60000, limit))
    balance = float(body.get("balance", 1000.0))
    timeframe = str(session["timeframe"])
    idempotency_key = f"{sym}:{timeframe}:{limit}:{balance:.8f}"

    active = await repo.get_active_backtest_job_by_key(idempotency_key)
    if active is not None:
        return JSONResponse(
            status_code=202,
            content={
                "job_id": active["job_id"],
                "status": active["status"],
                "symbol": sym,
                "timeframe": timeframe,
                "idempotency_key": idempotency_key,
                "created_at": active.get("created_at"),
                "updated_at": active.get("updated_at"),
                "reused_active_job": True,
            },
        )

    now = datetime.now(UTC)
    job_id = str(uuid4())
    job_doc = {
        "job_id": job_id,
        "symbol": sym,
        "timeframe": timeframe,
        "limit": limit,
        "initial_balance": balance,
        "idempotency_key": idempotency_key,
        "status": "queued",
        "created_at": now,
        "updated_at": now,
        "started_at": None,
        "completed_at": None,
        "backtest_result": None,
        "error_code": None,
        "error_message": None,
    }
    await repo.create_backtest_job(job_doc)
    logger.info(
        "onboarding_backtest_job_created",
        job_id=job_id,
        symbol=sym,
        timeframe=timeframe,
    )

    executor = _get_backtest_executor(request)

    async def _execute() -> None:
        try:
            await executor.run(lambda: _run_backtest_job(request, job_id))
        except TimeoutError:
            await repo.update_backtest_job(
                job_id,
                {
                    "status": "failed",
                    "completed_at": datetime.now(UTC),
                    "error_code": "timeout",
                    "error_message": "backtest job timed out",
                },
            )
            await repo.update_onboarding_session(sym, {"backtest_error": "TimeoutError"})
            logger.warning("onboarding_backtest_job_timeout", job_id=job_id, symbol=sym)
        except Exception as exc:
            await repo.update_backtest_job(
                job_id,
                {
                    "status": "failed",
                    "completed_at": datetime.now(UTC),
                    "error_code": "job_runner_error",
                    "error_message": str(exc)[:240] or type(exc).__name__,
                },
            )
            await repo.update_onboarding_session(sym, {"backtest_error": type(exc).__name__})
            logger.warning(
                "onboarding_backtest_job_runner_failed",
                job_id=job_id,
                symbol=sym,
                error_type=type(exc).__name__,
            )

    run_inline = bool(
        getattr(request.app.state.settings, "onboarding_backtest_job_run_inline", False)
    )
    if run_inline:
        await _execute()
        refreshed = await repo.get_backtest_job(job_id)
        if refreshed is not None:
            payload = _serialize_session(refreshed)
            payload["reused_active_job"] = False
            return JSONResponse(status_code=202, content=payload)
    else:
        asyncio.create_task(_execute())

    payload = _serialize_session(job_doc)
    payload["reused_active_job"] = False
    return JSONResponse(status_code=202, content=payload)


@router.get("/backtest-jobs/{job_id}")
async def get_backtest_job(request: Request, job_id: str) -> JSONResponse:
    repo = request.app.state.repository
    if repo is None:
        return _job_error_response("mongodb_unavailable", "MongoDB indisponível", status_code=503)
    job = await repo.get_backtest_job(job_id)
    if job is None:
        return _job_error_response("job_nao_encontrado", "Job não encontrado", status_code=404)
    return JSONResponse(status_code=200, content=_serialize_session(job))


@router.post("/{symbol}/approve")
async def approve_session(
    request: Request,
    symbol: str,
    body: Annotated[dict, Body()] = {},  # noqa: B006
) -> JSONResponse:
    if not _is_write_authorized(request):
        return _unauthorized_response()

    repo = request.app.state.repository
    if repo is None:
        return JSONResponse(status_code=503, content={"error": "mongodb_unavailable"})

    sym = symbol.upper()
    session = await repo.get_onboarding_session(sym)
    if session is None:
        return JSONResponse(status_code=404, content={"error": "sessao_nao_encontrada"})
    if session["status"] != "BACKTESTED":
        return JSONResponse(
            status_code=409,
            content={"error": "estado_invalido", "status_atual": session["status"]},
        )

    config_string = f"{sym}:{session['timeframe']}:{session['leverage']}"
    notes = str(body.get("notes", "")).strip() or None

    await repo.update_onboarding_session(
        sym,
        {
            "status": "APPROVED",
            "config_string": config_string,
            "notes": notes,
        },
    )
    updated = await repo.get_onboarding_session(sym)
    payload = _serialize_session(updated or {})
    payload.update(await _apply_symbol_timeframes_sync(request))
    return JSONResponse(status_code=200, content=payload)


@router.patch("/{symbol}")
async def patch_session(
    request: Request,
    symbol: str,
    body: Annotated[dict, Body()],
) -> JSONResponse:
    if not _is_write_authorized(request):
        return _unauthorized_response()

    repo = request.app.state.repository
    if repo is None:
        return JSONResponse(status_code=503, content={"error": "mongodb_unavailable"})

    current_symbol = symbol.upper()
    session = await repo.get_onboarding_session(current_symbol)
    if session is None:
        return JSONResponse(status_code=404, content={"error": "sessao_nao_encontrada"})

    editable_fields = {"symbol", "timeframe", "leverage", "notes"}
    if not any(field in body for field in editable_fields):
        return JSONResponse(
            status_code=422,
            content={"error": "payload_invalido", "detalhe": "Nenhum campo editavel informado"},
        )

    target_symbol = str(body.get("symbol", session["symbol"])).strip().upper()
    symbol_error = _validate_symbol(target_symbol)
    if symbol_error is not None:
        return symbol_error

    target_timeframe = str(body.get("timeframe", session["timeframe"])).strip()
    timeframe_error = _validate_timeframe(target_timeframe)
    if timeframe_error is not None:
        return timeframe_error

    target_leverage, leverage_error = _validate_leverage(body.get("leverage", session["leverage"]))
    if leverage_error is not None or target_leverage is None:
        return leverage_error

    notes = session.get("notes")
    if "notes" in body:
        notes = str(body.get("notes", "")).strip() or None

    if target_symbol != current_symbol:
        if target_symbol in _active_symbols(request):
            return JSONResponse(
                status_code=409,
                content={"error": "simbolo_ja_ativo", "symbol": target_symbol},
            )
        existing_target = await repo.get_onboarding_session(target_symbol)
        if existing_target is not None:
            return JSONResponse(
                status_code=409,
                content={"error": "sessao_ja_existe", "symbol": target_symbol},
            )
        cloned = dict(session)
        cloned.update(
            {
                "symbol": target_symbol,
                "timeframe": target_timeframe,
                "leverage": target_leverage,
                "notes": notes,
                "updated_at": datetime.now(UTC),
            }
        )
        if cloned.get("status") == "APPROVED":
            cloned["config_string"] = _compose_triplet(
                target_symbol, target_timeframe, target_leverage
            )
        await repo.create_onboarding_session(cloned)
        await repo.delete_onboarding_session(current_symbol)
        current_symbol = target_symbol
    else:
        update: dict[str, Any] = {}
        if target_timeframe != session.get("timeframe"):
            update["timeframe"] = target_timeframe
        if target_leverage != session.get("leverage"):
            update["leverage"] = target_leverage
        if notes != session.get("notes"):
            update["notes"] = notes
        if session.get("status") == "APPROVED":
            new_config_string = _compose_triplet(target_symbol, target_timeframe, target_leverage)
            if new_config_string != session.get("config_string"):
                update["config_string"] = new_config_string
        if update:
            await repo.update_onboarding_session(current_symbol, update)

    updated = await repo.get_onboarding_session(current_symbol)
    payload = _serialize_session(updated or {})
    if payload.get("status") == "APPROVED":
        payload.update(await _apply_symbol_timeframes_sync(request))
    return JSONResponse(status_code=200, content=payload)


@router.post("/{symbol}/market-analysis")
async def run_market_analysis(request: Request, symbol: str) -> JSONResponse:
    if not _is_write_authorized(request):
        return _unauthorized_response()

    repo = request.app.state.repository
    if repo is None:
        return JSONResponse(status_code=503, content={"error": "mongodb_unavailable"})

    sym = symbol.upper()
    session = await repo.get_onboarding_session(sym)
    if session is None:
        return JSONResponse(status_code=404, content={"error": "sessao_nao_encontrada"})

    try:
        from src.config.settings import get_settings
        from src.exchange.binance_client import BinanceClient

        settings = get_settings()
        client = BinanceClient(settings)
        await client.connect()
        try:
            raw_df = await client.fetch_ohlcv_with_retry(
                sym,
                str(session["timeframe"]),
                limit=_MARKET_ANALYSIS_CANDLES_LIMIT,
            )
        finally:
            await client.close()

        if raw_df.empty:
            return JSONResponse(
                status_code=503,
                content={"error": "market_analysis_unavailable", "tipo": "EmptyOHLCV"},
            )

        closed_df = raw_df.iloc[:-1].copy() if len(raw_df) > 1 else raw_df.copy()
        if len(closed_df) < 50:
            return JSONResponse(
                status_code=503,
                content={"error": "market_analysis_unavailable", "tipo": "InsufficientCandles"},
            )

        enriched = compute_all(closed_df)
        signal_engine = SignalEngine(risk_reward_ratio=float(settings.risk_reward_ratio))
        signal = signal_engine.evaluate(sym, str(session["timeframe"]), closed_df)

        payload = {
            "symbol": sym,
            "timeframe": session["timeframe"],
            "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "signal_detected": signal is not None,
            "signal": _serialize_signal(signal) if signal is not None else None,
            "context": _serialize_market_context(enriched),
        }
        return JSONResponse(status_code=200, content=payload)
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"error": "market_analysis_unavailable", "tipo": type(exc).__name__},
        )
