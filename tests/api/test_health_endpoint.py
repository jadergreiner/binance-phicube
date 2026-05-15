"""Testes do endpoint GET /health (SPEC_007 + SPEC_017)."""

from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.health import router


def _make_app(repo=None) -> FastAPI:
    """Cria app de teste com repositório injetado no state."""
    app = FastAPI()
    app.include_router(router)
    if repo is not None:
        app.state.repository = repo
    return app


def _make_repo(ping_ok: bool = True, heartbeat_result=None, heartbeat_raises: bool = False):
    mock_repo = AsyncMock()
    mock_repo.database = AsyncMock()
    if ping_ok:
        mock_repo.database.command = AsyncMock(return_value={"ok": 1})
    else:
        mock_repo.database.command = AsyncMock(side_effect=Exception("connection refused"))
    if heartbeat_raises:
        mock_repo.get_last_heartbeat_at = AsyncMock(side_effect=Exception("mongo down"))
    else:
        mock_repo.get_last_heartbeat_at = AsyncMock(return_value=heartbeat_result)
    return mock_repo


class TestHealthEndpoint:
    """TEST_007_07, TEST_007_08 — endpoint GET /health."""

    def test_retorna_200_quando_mongodb_ok(self) -> None:
        """TEST_007_07: MongoDB acessível → 200 com status ok."""
        mock_repo = _make_repo(ping_ok=True, heartbeat_result=None)

        app = _make_app(repo=mock_repo)
        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["mongodb"] == "ok"
        assert "bot_process" in data
        assert "timestamp" in data
        assert "predictive_circuit_breaker_skips_total" in data

    def test_retorna_503_quando_mongodb_falha(self) -> None:
        """TEST_007_08: MongoDB inacessível → 503 com status error."""
        mock_repo = _make_repo(ping_ok=False)

        app = _make_app(repo=mock_repo)
        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "error"
        assert data["mongodb"] == "error"
        assert "predictive_circuit_breaker_skips_total" in data

    def test_retorna_503_sem_repositorio(self) -> None:
        """Repositório ausente em app.state → 503 gracioso."""
        app = _make_app(repo=None)
        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "error"
        assert data["mongodb"] == "error"
        assert data["bot_process"] == "unknown"
        assert "predictive_circuit_breaker_skips_total" in data
