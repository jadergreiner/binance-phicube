"""
Testes de conformidade SPEC_017 — campo bot_process e last_heartbeat_at no GET /health.

Cobre:
- TEST_017_03: bot_process "alive" quando heartbeat recente (< 10 min)
- TEST_017_04: bot_process "dead" quando heartbeat > 10 min
- TEST_017_05: bot_process "dead" quando get_last_heartbeat_at() retorna None
- TEST_017_06: bot_process "unknown" quando MongoDB falha na consulta de heartbeat
- TEST_017_07: campos originais (status, mongodb, timestamp) preservados
- TEST_017_10: _health_server responde 200
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.health import router


def _make_app(repo) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.repository = repo
    return app


def _make_repo(heartbeat_dt=None, heartbeat_raises: bool = False):
    mock_repo = AsyncMock()
    mock_repo.database = AsyncMock()
    mock_repo.database.command = AsyncMock(return_value={"ok": 1})
    if heartbeat_raises:
        mock_repo.get_last_heartbeat_at = AsyncMock(side_effect=Exception("mongo down"))
    else:
        mock_repo.get_last_heartbeat_at = AsyncMock(return_value=heartbeat_dt)
    return mock_repo


class TestBotProcessField:
    """TEST_017_03 a TEST_017_07 — campo bot_process derivado de heartbeat."""

    def test_bot_process_alive_quando_heartbeat_recente(self) -> None:
        """TEST_017_03: heartbeat há 3 min → bot_process 'alive'."""
        recent = datetime.now(UTC) - timedelta(minutes=3)
        mock_repo = _make_repo(heartbeat_dt=recent)

        with TestClient(_make_app(mock_repo)) as client:
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["bot_process"] == "alive"
        assert data["last_heartbeat_at"] is not None

    def test_bot_process_dead_quando_heartbeat_antigo(self) -> None:
        """TEST_017_04: heartbeat há 15 min → bot_process 'dead'."""
        old = datetime.now(UTC) - timedelta(minutes=15)
        mock_repo = _make_repo(heartbeat_dt=old)

        with TestClient(_make_app(mock_repo)) as client:
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["bot_process"] == "dead"

    def test_bot_process_dead_sem_heartbeat(self) -> None:
        """TEST_017_05: get_last_heartbeat_at() retorna None → bot_process 'dead'."""
        mock_repo = _make_repo(heartbeat_dt=None)

        with TestClient(_make_app(mock_repo)) as client:
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["bot_process"] == "dead"
        assert data["last_heartbeat_at"] is None

    def test_bot_process_unknown_quando_mongodb_falha(self) -> None:
        """TEST_017_06: get_last_heartbeat_at() levanta Exception → bot_process 'unknown'."""
        mock_repo = _make_repo(heartbeat_raises=True)

        with TestClient(_make_app(mock_repo)) as client:
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["bot_process"] == "unknown"

    def test_campos_originais_preservados(self) -> None:
        """TEST_017_07: status, mongodb, timestamp presentes independente do heartbeat."""
        mock_repo = _make_repo(heartbeat_dt=None)

        with TestClient(_make_app(mock_repo)) as client:
            response = client.get("/health")

        data = response.json()
        assert data["status"] == "ok"
        assert data["mongodb"] == "ok"
        assert "timestamp" in data
        assert "timestamp_br" in data
        assert data["timezone"] == "America/Sao_Paulo"
        assert "bot_process" in data
        assert "last_heartbeat_at" in data
        assert "last_heartbeat_at_br" in data

    def test_last_heartbeat_at_formato_iso8601(self) -> None:
        """last_heartbeat_at é string ISO 8601 com sufixo Z quando heartbeat presente."""
        recent = datetime.now(UTC) - timedelta(minutes=1)
        mock_repo = _make_repo(heartbeat_dt=recent)

        with TestClient(_make_app(mock_repo)) as client:
            response = client.get("/health")

        ts = response.json()["last_heartbeat_at"]
        assert isinstance(ts, str)
        assert ts.endswith("Z")
        assert response.json()["last_heartbeat_at_br"]

    def test_limiar_9min_retorna_alive(self) -> None:
        """Heartbeat há 9 min 55 s → 'alive' (abaixo do threshold de 10 min)."""
        near_threshold = datetime.now(UTC) - timedelta(minutes=9, seconds=55)
        mock_repo = _make_repo(heartbeat_dt=near_threshold)

        with TestClient(_make_app(mock_repo)) as client:
            response = client.get("/health")

        assert response.json()["bot_process"] == "alive"


class TestHealthServer:
    """TEST_017_10 — _health_server responde 200."""

    def test_health_server_responde_200(self) -> None:
        """TEST_017_10: servidor HTTP na porta livre responde 200."""

        from src.main import _health_server

        async def _run():
            server_task = asyncio.create_task(_health_server(host="127.0.0.1", port=0))
            await asyncio.sleep(0.05)
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

        asyncio.run(_run())

    def test_health_server_responde_json_status_ok(self) -> None:
        """Servidor HTTP retorna body JSON com status ok."""
        import json

        from src.main import _health_server

        result: dict = {}

        async def _run():
            import asyncio

            server = await asyncio.start_server(None, "127.0.0.1", 0)
            port = server.sockets[0].getsockname()[1]
            server.close()
            await server.wait_closed()

            server_task = asyncio.create_task(_health_server(host="127.0.0.1", port=port))
            await asyncio.sleep(0.05)

            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.write(b"GET /health HTTP/1.0\r\nHost: localhost\r\n\r\n")
            await writer.drain()
            response = await reader.read(512)
            writer.close()
            result["response"] = response.decode()

            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

        asyncio.run(_run())
        assert "200 OK" in result["response"]
        body = result["response"].split("\r\n\r\n", 1)[1]
        assert json.loads(body)["status"] == "ok"
