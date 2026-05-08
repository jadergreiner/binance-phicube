"""Rotas de trades para visibilidade operacional do dashboard."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.api.datetime_utils import (
    BRAZIL_TIMEZONE,
    enrich_datetime_fields,
    to_brazil_datetime_str,
    to_iso8601_utc,
)

router = APIRouter()


def _normalize_trade(trade: dict[str, Any]) -> dict[str, Any]:
    return enrich_datetime_fields(trade, ("opened_at", "closed_at"))


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_symbol_for_match(symbol: str | None) -> str:
    raw = (symbol or "").strip().upper()
    if not raw:
        return ""
    normalized = raw.replace("/", "").replace(":", "")
    if normalized.endswith("USDTUSDT"):
        normalized = normalized.removesuffix("USDT")
    return normalized


def _calc_unrealized_pnl(
    *,
    direction: str | None,
    entry_price: float | None,
    current_price: float | None,
    quantity: float | None,
) -> float | None:
    if entry_price is None or current_price is None or quantity is None:
        return None
    if quantity <= 0:
        return None
    side = (direction or "").upper()
    side_mult = 1.0 if side == "LONG" else -1.0 if side == "SHORT" else None
    if side_mult is None:
        return None
    return (current_price - entry_price) * quantity * side_mult


def _build_open_trade_payload(
    trade: dict[str, Any],
    *,
    mark_price: float | None,
    unrealized_pnl_from_position: float | None,
) -> dict[str, Any]:
    entry_price = _to_float(trade.get("entry_price"))
    quantity = _to_float(trade.get("quantity"))
    unrealized_pnl = (
        unrealized_pnl_from_position
        if unrealized_pnl_from_position is not None
        else _calc_unrealized_pnl(
            direction=str(trade.get("direction", "")),
            entry_price=entry_price,
            current_price=mark_price,
            quantity=quantity,
        )
    )
    margin_used = _to_float(trade.get("margin_used_usdt"))
    if margin_used is None:
        margin_used = _to_float(trade.get("margin_used"))
    return {
        "opened_at": trade.get("opened_at"),
        "symbol": trade.get("symbol"),
        "margin_used_usdt": margin_used,
        "entry_price": entry_price,
        "current_price": mark_price,
        "unrealized_pnl_usdt": unrealized_pnl,
    }


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
    generated_at = to_iso8601_utc(datetime.now(UTC))
    return JSONResponse(
        status_code=200,
        content={
            "trades": normalized_trades,
            "total": len(normalized_trades),
            "generated_at": generated_at,
            "generated_at_br": to_brazil_datetime_str(generated_at),
            "timezone": BRAZIL_TIMEZONE,
        },
    )


@router.get("/trades/open")
async def get_open_trades(request: Request) -> JSONResponse:
    """Retorna trades abertos com enrich de preço atual e PnL não realizado."""
    repo = getattr(request.app.state, "repository", None)
    if repo is None:
        return JSONResponse(status_code=503, content={"detail": "Repositório indisponível"})

    try:
        trades = await repo.get_open_trades()
    except Exception:
        return JSONResponse(status_code=503, content={"detail": "Repositório indisponível"})

    stream = getattr(request.app.state, "position_stream", None)
    positions_by_symbol: dict[str, Any] = {}
    if stream is not None:
        try:
            positions = list(stream.get_positions())
            for position in positions:
                symbol = str(getattr(position, "symbol", "")).upper()
                if not symbol:
                    continue
                positions_by_symbol[symbol] = position
                normalized = _normalize_symbol_for_match(symbol)
                if normalized:
                    positions_by_symbol[normalized] = position
        except Exception:
            positions_by_symbol = {}

    payload = []
    for trade in trades:
        symbol = str(trade.get("symbol", ""))
        position = positions_by_symbol.get(symbol.upper())
        if position is None:
            position = positions_by_symbol.get(_normalize_symbol_for_match(symbol))
        mark_price = _to_float(getattr(position, "mark_price", None))
        unrealized_pnl = _to_float(getattr(position, "unrealized_pnl_usdt", None))
        payload.append(
            _normalize_trade(
                _build_open_trade_payload(
                    trade,
                    mark_price=mark_price,
                    unrealized_pnl_from_position=unrealized_pnl,
                )
            )
        )

    payload = sorted(payload, key=lambda t: t.get("opened_at") or "", reverse=True)
    generated_at = to_iso8601_utc(datetime.now(UTC))
    return JSONResponse(
        status_code=200,
        content={
            "trades": payload,
            "total": len(payload),
            "generated_at": generated_at,
            "generated_at_br": to_brazil_datetime_str(generated_at),
            "timezone": BRAZIL_TIMEZONE,
        },
    )
