"""Rotas REST e WebSocket do dashboard de consulta de posições."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse

from src.dashboard.models import AccountSummary, PositionView, build_account_summary

router = APIRouter()


def _to_iso8601(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _serialize_position(position: PositionView) -> dict[str, Any]:
    return {
        "symbol": position.symbol,
        "side": position.side,
        "quantity": position.quantity,
        "leverage": position.leverage,
        "entry_price": position.entry_price,
        "mark_price": position.mark_price,
        "unrealized_pnl_usdt": position.unrealized_pnl_usdt,
        "margin_used_usdt": position.margin_used_usdt,
        "liquidation_price": position.liquidation_price,
        "updated_at": _to_iso8601(position.updated_at),
    }


def _serialize_summary(summary: AccountSummary) -> dict[str, Any]:
    return {
        "total_exposure_usdt": summary.total_exposure_usdt,
        "total_margin_used_usdt": summary.total_margin_used_usdt,
        "total_unrealized_pnl_usdt": summary.total_unrealized_pnl_usdt,
        "connection_status": summary.connection_status,
        "last_update_at": _to_iso8601(summary.last_update_at),
    }


def _get_position_stream(request: Request) -> Any:
    stream = getattr(request.app.state, "position_stream", None)
    if stream is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "offline"},
        )
    return stream


def _build_snapshot(stream: Any) -> dict[str, Any]:
    positions = list(stream.get_positions())
    connection_status = stream.get_status()
    summary = build_account_summary(positions, connection_status)
    return {
        "positions": [_serialize_position(position) for position in positions],
        "summary": _serialize_summary(summary),
        "status": connection_status,
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

    snapshot = _build_snapshot(stream)
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

    return JSONResponse(content=_build_snapshot(stream))


@router.websocket("/ws/positions")
async def websocket_positions(websocket: WebSocket) -> None:
    """Emite snapshots completos do dashboard sempre que houver atualização."""
    await websocket.accept()

    app = websocket.scope["app"]
    stream = _attach_update_callback(app)
    clients = _ensure_websocket_clients(app)
    clients.append(websocket)

    try:
        await websocket.send_json(_build_snapshot(stream))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in clients:
            clients.remove(websocket)