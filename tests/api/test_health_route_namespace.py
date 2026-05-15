"""Evita colisao de namespace entre health do stream e health operacional."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.health import router as operational_health_router
from src.api.routes.positions import router as positions_router


class _FakeStream:
    def get_status(self) -> str:
        return "online"


def test_system_health_permanece_acessivel_quando_positions_router_ja_registrou_health() -> None:
    app = FastAPI()
    app.include_router(positions_router)
    app.include_router(operational_health_router)

    repo = AsyncMock()
    repo.database.command = AsyncMock(return_value={"ok": 1})
    repo.get_last_heartbeat_at = AsyncMock(return_value=datetime.now(UTC))
    app.state.repository = repo
    app.state.position_stream = _FakeStream()

    with TestClient(app) as client:
        stream_health = client.get("/positions/health")
        system_health = client.get("/system/health")

    assert stream_health.status_code == 200
    assert stream_health.json() == {"status": "online"}

    assert system_health.status_code == 200
    payload = system_health.json()
    assert payload["status"] == "ok"
    assert payload["mongodb"] == "ok"
    assert payload["bot_process"] == "alive"
    assert payload["last_heartbeat_at"] is not None
    assert payload["last_heartbeat_at_br"] is not None
    assert payload["timestamp_br"] is not None
    assert payload["timezone"] == "America/Sao_Paulo"
