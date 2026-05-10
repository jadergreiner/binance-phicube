"""Rotas REST e WebSocket do dashboard de consulta de posições."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse

from src.api.datetime_utils import BRAZIL_TIMEZONE, to_brazil_datetime_str, to_iso8601_utc
from src.common.decorators import safe_async
from src.dashboard.analysis import build_market_analysis
from src.dashboard.models import AccountSummary, PositionView, build_account_summary
from src.monitoring.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


def _serialize_position(
    position: PositionView, sl_tp_map: dict[str, dict[str, float | None]]
) -> dict[str, Any]:
    position_size_usdt = getattr(position, "position_size_usdt", None)
    if position_size_usdt is None and hasattr(position, "margin_used_usdt"):
        try:
            if position.margin_used_usdt >= 0 and position.leverage > 0:
                position_size_usdt = position.margin_used_usdt * position.leverage
        except Exception:
            position_size_usdt = None

    roi_adjusted_pct = getattr(position, "roi_adjusted_pct", None)
    if roi_adjusted_pct is None and position_size_usdt is not None and position_size_usdt > 0:
        try:
            roi_adjusted_pct = Decimal(str(position.unrealized_pnl_usdt))
            roi_adjusted_pct = (
                roi_adjusted_pct / Decimal(str(position_size_usdt)) * Decimal("100")
            ).quantize(Decimal("0.0000000000000001"))
            roi_adjusted_pct = float(roi_adjusted_pct)
        except (Exception, InvalidOperation):
            roi_adjusted_pct = None

    sl_tp_data = sl_tp_map.get(position.symbol, {})
    updated_at = to_iso8601_utc(position.updated_at)
    return {
        "symbol": position.symbol,
        "side": position.side,
        "quantity": position.quantity,
        "leverage": position.leverage,
        "entry_price": position.entry_price,
        "sl_price": sl_tp_data.get("sl_price"),
        "tp_price": sl_tp_data.get("tp_price"),
        "mark_price": position.mark_price,
        "unrealized_pnl_usdt": position.unrealized_pnl_usdt,
        "margin_used_usdt": position.margin_used_usdt,
        "position_size_usdt": position_size_usdt,
        "roi_adjusted_pct": roi_adjusted_pct,
        "liquidation_price": position.liquidation_price,
        "updated_at": updated_at,
        "updated_at_br": to_brazil_datetime_str(updated_at),
    }


def _serialize_summary(summary: AccountSummary) -> dict[str, Any]:
    last_update_at = to_iso8601_utc(summary.last_update_at)
    return {
        "total_exposure_usdt": summary.total_exposure_usdt,
        "total_margin_used_usdt": summary.total_margin_used_usdt,
        "total_unrealized_pnl_usdt": summary.total_unrealized_pnl_usdt,
        "account_equity_usdt": summary.account_equity_usdt,
        "exposure_to_equity_ratio": summary.exposure_to_equity_ratio,
        "connection_status": summary.connection_status,
        "last_update_at": last_update_at,
        "last_update_at_br": to_brazil_datetime_str(last_update_at),
    }


def _serialize_market_analysis(analysis: Any) -> dict[str, Any]:
    raw_bias_views = getattr(analysis, "bias_views", None)
    serialized_bias_views: dict[str, Any] | None = None
    if raw_bias_views is not None:
        serialized_bias_views = {
            "active": raw_bias_views.active,
            "views": [
                {
                    "id": view.id,
                    "direction": view.direction,
                    "confidence": view.confidence,
                    "score": view.score,
                    "reason": view.reason,
                    "metrics": view.metrics,
                }
                for view in raw_bias_views.views
            ],
            "divergence": {
                "has_divergence": raw_bias_views.divergence.has_divergence,
                "summary": raw_bias_views.divergence.summary,
            },
        }
    return {
        "bias": {
            "direction": analysis.bias.direction,
            "confidence": analysis.bias.confidence,
            "score": analysis.bias.score,
            "reason": analysis.bias.reason,
        },
        "bias_views": serialized_bias_views,
        "opportunities": [
            {
                "symbol": opportunity.symbol,
                "direction": opportunity.direction,
                "action": opportunity.action,
                "rationale": opportunity.rationale,
                "exposure_usdt": opportunity.exposure_usdt,
            }
            for opportunity in analysis.opportunities
        ],
    }


def _get_position_stream(request: Request) -> Any:
    stream = getattr(request.app.state, "position_stream", None)
    if stream is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "offline"},
        )
    return stream


def _get_repository(app: Any) -> Any:
    return getattr(app.state, "repository", None)


@safe_async(log_event="dashboard_positions_sl_tp_enrichment_failed", fallback={})
async def _load_open_trade_sl_tp(app: Any) -> dict[str, dict[str, float | None]]:
    repo = _get_repository(app)
    if repo is None:
        return {}
    return await repo.get_open_trade_sl_tp()


def _normalize_signal_diag_time(value: Any) -> str | None:
    if value is None:
        return None
    return to_iso8601_utc(value)


def _serialize_signal_telemetry_row(item: dict[str, Any]) -> dict[str, Any]:
    evaluated_at = _normalize_signal_diag_time(item.get("evaluated_at") or item.get("ts"))
    candle_open_time = _normalize_signal_diag_time(item.get("candle_open_time"))
    return {
        "symbol": item.get("symbol"),
        "timeframe": item.get("timeframe"),
        "decision": item.get("decision") or "UNKNOWN",
        "signal_generated": bool(item.get("signal_generated")),
        "reason": item.get("reason") or "indisponivel",
        "evaluated_at": evaluated_at,
        "evaluated_at_br": to_brazil_datetime_str(evaluated_at),
        "candle_open_time": candle_open_time,
        "candle_open_time_br": to_brazil_datetime_str(candle_open_time),
        "long_conditions": item.get("long_conditions"),
        "short_conditions": item.get("short_conditions"),
    }


@safe_async(log_event="dashboard_signal_telemetry_load_failed", fallback=[])
async def _load_signal_telemetry(app: Any) -> list[dict[str, Any]]:
    repo = _get_repository(app)
    if repo is None:
        return []
    get_latest = getattr(repo, "get_latest_signal_diagnostics", None)
    if not callable(get_latest):
        return []
    rows = await get_latest(limit=10)
    return [_serialize_signal_telemetry_row(row) for row in rows if isinstance(row, dict)]


async def _build_snapshot(app: Any, stream: Any) -> dict[str, Any]:
    positions = list(stream.get_positions())
    connection_status = stream.get_status()
    account_equity_fn = getattr(stream, "get_account_equity_usdt", None)
    account_equity_usdt = (
        account_equity_fn()
        if callable(account_equity_fn)
        else getattr(stream, "_account_equity_usdt", None)
    )
    summary = build_account_summary(
        positions,
        connection_status,
        account_equity_usdt=account_equity_usdt,
    )
    market_analysis = build_market_analysis(positions)
    sl_tp_map = await _load_open_trade_sl_tp(app)
    signal_telemetry = await _load_signal_telemetry(app)
    return {
        "positions": [_serialize_position(position, sl_tp_map) for position in positions],
        "summary": _serialize_summary(summary),
        "status": connection_status,
        "analysis": _serialize_market_analysis(market_analysis),
        "signal_telemetry": signal_telemetry,
        "timezone": BRAZIL_TIMEZONE,
    }


def _is_stream_active(stream: Any) -> bool:
    return stream.get_status() != "offline"


def _ensure_websocket_clients(app: Any) -> list[WebSocket]:
    clients = getattr(app.state, "ws_clients", None)
    if clients is None:
        clients = []
        app.state.ws_clients = clients
    return clients


async def _broadcast_snapshot(app: Any, stream: Any) -> None:
    clients = _ensure_websocket_clients(app)
    if not clients:
        return

    snapshot = await _build_snapshot(app, stream)
    for websocket in list(clients):
        try:
            await websocket.send_json(snapshot)
        except Exception:
            if websocket in clients:
                clients.remove(websocket)


def _attach_update_callback(app: Any) -> Any:
    stream = getattr(app.state, "position_stream", None)
    if stream is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "offline"},
        )

    async def _on_update(updated_stream: Any) -> None:
        await _broadcast_snapshot(app, updated_stream)

    stream.on_update = _on_update
    return stream


@router.get("/health")
async def get_health(request: Request) -> JSONResponse:
    """Expõe o estado atual do stream do dashboard."""
    stream = _get_position_stream(request)
    payload = {"status": stream.get_status()}
    if not _is_stream_active(stream):
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)

    return JSONResponse(content=payload)


@router.get("/positions")
async def get_positions(request: Request) -> JSONResponse:
    """Retorna o snapshot atual das posições abertas."""
    stream = _get_position_stream(request)
    if not _is_stream_active(stream):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": stream.get_status()},
        )

    return JSONResponse(content=await _build_snapshot(request.app, stream))


@router.websocket("/ws/positions")
async def websocket_positions(websocket: WebSocket) -> None:
    """Emite snapshots completos do dashboard sempre que houver atualização."""
    await websocket.accept()

    app = websocket.scope["app"]
    stream = _attach_update_callback(app)
    clients = _ensure_websocket_clients(app)
    clients.append(websocket)

    try:
        await websocket.send_json(await _build_snapshot(app, stream))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in clients:
            clients.remove(websocket)
