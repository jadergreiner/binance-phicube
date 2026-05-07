"""Rotas REST para onboarding de novos símbolos (SPEC_019)."""

from __future__ import annotations

import dataclasses
import math
import re
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

_VALID_TIMEFRAMES = {"1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"}
_SYMBOL_RE = re.compile(r"^[A-Z]{2,15}USDT$")
_COMMODITIES = frozenset({"XPTUSDT", "COPPERUSDT"})


def _serialize_session(doc: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in doc.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat().replace("+00:00", "Z")
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


@router.get("")
async def list_sessions(request: Request) -> JSONResponse:
    repo = request.app.state.repository
    if repo is None:
        return JSONResponse(status_code=503, content={"error": "mongodb_unavailable"})
    sessions = await repo.list_onboarding_sessions()
    return JSONResponse(status_code=200, content=[_serialize_session(s) for s in sessions])


@router.post("")
async def create_session(
    request: Request,
    body: Annotated[dict, Body()],
) -> JSONResponse:
    repo = request.app.state.repository
    if repo is None:
        return JSONResponse(status_code=503, content={"error": "mongodb_unavailable"})

    symbol = str(body.get("symbol", "")).strip().upper()
    timeframe = str(body.get("timeframe", "")).strip()
    leverage_raw = body.get("leverage")

    # Validações básicas
    if not _SYMBOL_RE.match(symbol):
        return JSONResponse(
            status_code=422,
            content={"error": "symbol_invalido", "detalhe": "Formato esperado: XXXXUSDT"},
        )
    if timeframe not in _VALID_TIMEFRAMES:
        return JSONResponse(
            status_code=422,
            content={"error": "timeframe_invalido", "validos": sorted(_VALID_TIMEFRAMES)},
        )
    try:
        leverage = int(leverage_raw)  # type: ignore[arg-type]
        if not (1 <= leverage <= 20):
            raise ValueError
    except (TypeError, ValueError):
        return JSONResponse(
            status_code=422,
            content={"error": "leverage_invalido", "detalhe": "Deve ser inteiro entre 1 e 20"},
        )

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
    repo = request.app.state.repository
    if repo is None:
        return JSONResponse(status_code=503, content={"error": "mongodb_unavailable"})
    deleted = await repo.delete_onboarding_session(symbol.upper())
    if not deleted:
        return JSONResponse(status_code=404, content={"error": "sessao_nao_encontrada"})
    return JSONResponse(status_code=204, content=None)


@router.post("/{symbol}/backtest")
async def run_backtest(
    request: Request,
    symbol: str,
    body: Annotated[dict, Body()] = {},  # noqa: B006
) -> JSONResponse:
    repo = request.app.state.repository
    if repo is None:
        return JSONResponse(status_code=503, content={"error": "mongodb_unavailable"})

    sym = symbol.upper()
    session = await repo.get_onboarding_session(sym)
    if session is None:
        return JSONResponse(status_code=404, content={"error": "sessao_nao_encontrada"})
    if session["status"] in ("APPROVED",):
        return JSONResponse(
            status_code=409,
            content={"error": "estado_invalido", "status_atual": session["status"]},
        )

    limit = int(body.get("limit", 35000))
    limit = max(50, min(60000, limit))
    balance = float(body.get("balance", 1000.0))

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
                sym,
                session["timeframe"],
                limit=limit,
                initial_balance=balance,
            )
        finally:
            await client.close()

        result_dict = _serialize_backtest(result)
        await repo.update_onboarding_session(
            sym,
            {
                "status": "BACKTESTED",
                "backtest_result": result_dict,
                "backtest_limit": limit,
                "backtest_error": None,
            },
        )
    except Exception as exc:
        await repo.update_onboarding_session(
            sym,
            {"backtest_error": type(exc).__name__},
        )
        return JSONResponse(
            status_code=503,
            content={"error": "backtest_falhou", "tipo": type(exc).__name__},
        )

    updated = await repo.get_onboarding_session(sym)
    return JSONResponse(status_code=200, content=_serialize_session(updated or {}))


@router.post("/{symbol}/approve")
async def approve_session(
    request: Request,
    symbol: str,
    body: Annotated[dict, Body()] = {},  # noqa: B006
) -> JSONResponse:
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
    return JSONResponse(status_code=200, content=_serialize_session(updated or {}))
