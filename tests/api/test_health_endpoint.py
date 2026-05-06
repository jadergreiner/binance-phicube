"""Testes do endpoint GET /health (SPEC_007 task_003)."""

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


class TestHealthEndpoint:
    """TEST_007_07 e TEST_007_08 — endpoint GET /health."""

    def test_retorna_200_quando_mongodb_ok(self) -> None:
        """TEST_007_07: MongoDB acessível → 200 com status ok."""
        mock_repo = AsyncMock()
        mock_repo.database = AsyncMock()
        mock_repo.database.command = AsyncMock(return_value={"ok": 1})

        app = _make_app(repo=mock_repo)
        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["mongodb"] == "ok"
        assert data["bot_process"] == "unknown"
        assert "timestamp" in data

    def test_retorna_503_quando_mongodb_falha(self) -> None:
        """TEST_007_08: MongoDB inacessível → 503 com status error."""
        mock_repo = AsyncMock()
        mock_repo.database = AsyncMock()
        mock_repo.database.command = AsyncMock(side_effect=Exception("connection refused"))

        app = _make_app(repo=mock_repo)
        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "error"
        assert data["mongodb"] == "error"

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

    def test_bot_process_sempre_unknown(self) -> None:
        """bot_process nunca expõe estado interno do bot — sempre 'unknown'."""
        mock_repo = AsyncMock()
        mock_repo.database = AsyncMock()
        mock_repo.database.command = AsyncMock(return_value={"ok": 1})

        app = _make_app(repo=mock_repo)
        with TestClient(app) as client:
            response = client.get("/health")

        assert response.json()["bot_process"] == "unknown"
