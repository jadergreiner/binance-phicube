"""Testes do endpoint GET /performance (SPEC_006 task_004)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


def _make_app(repo=None):
    """Cria app de teste com repositório injetado no state."""
    with patch("motor.motor_asyncio.AsyncIOMotorClient"):
        from fastapi import FastAPI

        from src.api.routes.performance import router

        app = FastAPI()
        app.include_router(router)
        if repo is not None:
            app.state.repository = repo
        return app


class TestPerformanceEndpoint:
    """TEST_006_07 e TEST_006_08 — endpoint GET /performance."""

    def test_retorna_200_com_metricas(self) -> None:
        """TEST_006_07: endpoint retorna 200 com JSON de métricas."""
        mock_repo = AsyncMock()
        mock_repo.get_performance_metrics = AsyncMock(
            return_value={
                "total_trades": 5,
                "win_rate_pct": 60.0,
                "total_pnl_usdt": 31.0,
                "avg_rrr": 1.8,
                "max_drawdown_usdt": -14.0,
                "profit_factor": 3.18,
            }
        )
        app = _make_app(repo=mock_repo)

        with TestClient(app) as client:
            response = client.get("/performance")

        assert response.status_code == 200
        data = response.json()
        assert data["total_trades"] == 5
        assert data["win_rate_pct"] == 60.0
        assert data["total_pnl_usdt"] == 31.0
        assert "generated_at" in data

    def test_retorna_200_com_zeros_quando_sem_trades(self) -> None:
        """Sem trades fechados → zeros, status 200."""
        mock_repo = AsyncMock()
        mock_repo.get_performance_metrics = AsyncMock(
            return_value={
                "total_trades": 0,
                "win_rate_pct": 0.0,
                "total_pnl_usdt": 0.0,
                "avg_rrr": 0.0,
                "max_drawdown_usdt": 0.0,
                "profit_factor": 0.0,
            }
        )
        app = _make_app(repo=mock_repo)

        with TestClient(app) as client:
            response = client.get("/performance")

        assert response.status_code == 200
        assert response.json()["total_trades"] == 0

    def test_retorna_503_sem_repositorio(self) -> None:
        """TEST_006_08: repositório ausente → 503, bot não é afetado."""
        app = _make_app(repo=None)

        with TestClient(app) as client:
            response = client.get("/performance")

        assert response.status_code == 503
        assert response.json()["error"] == "database_unavailable"

    def test_retorna_503_quando_mongo_falha(self) -> None:
        """TEST_006_08: exceção no repositório → 503."""
        mock_repo = AsyncMock()
        mock_repo.get_performance_metrics = AsyncMock(side_effect=Exception("mongo down"))
        app = _make_app(repo=mock_repo)

        with TestClient(app) as client:
            response = client.get("/performance")

        assert response.status_code == 503
        assert response.json()["error"] == "database_unavailable"
