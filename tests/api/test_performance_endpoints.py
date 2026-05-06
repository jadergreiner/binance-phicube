"""Testes de rastreabilidade SPEC_010 para GET /performance (complementa SPEC_006).

TEST_010_01 e TEST_010_02 validam que o endpoint global continua sem regressão
após as adições de frontend da SPEC_010.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


def _make_app(repo=None):
    with patch("motor.motor_asyncio.AsyncIOMotorClient"):
        from fastapi import FastAPI

        from src.api.routes.performance import router

        app = FastAPI()
        app.include_router(router)
        if repo is not None:
            app.state.repository = repo
        return app


def _mock_repo():
    mock_repo = AsyncMock()
    mock_repo.get_performance_metrics = AsyncMock(
        return_value={
            "total_trades": 10,
            "win_rate_pct": 60.0,
            "total_pnl_usdt": 50.0,
            "avg_rrr": 1.5,
            "max_drawdown_usdt": -20.0,
            "profit_factor": 2.0,
        }
    )
    return mock_repo


class TestPerformanceGlobalEndpointSpec010:
    """TEST_010_01 e TEST_010_02 — GET /performance sem regressão (INV-010-04)."""

    def test_retorna_200_com_metricas_globais(self) -> None:
        """TEST_010_01: endpoint retorna 200 com as 6 métricas e generated_at."""
        app = _make_app(repo=_mock_repo())

        with TestClient(app) as client:
            response = client.get("/performance")

        assert response.status_code == 200
        data = response.json()
        assert data["total_trades"] == 10
        assert data["win_rate_pct"] == 60.0
        assert data["total_pnl_usdt"] == 50.0
        assert data["avg_rrr"] == 1.5
        assert data["max_drawdown_usdt"] == -20.0
        assert data["profit_factor"] == 2.0
        assert "generated_at" in data

    def test_retorna_503_sem_repositorio(self) -> None:
        """TEST_010_02: repositório ausente → 503."""
        app = _make_app(repo=None)

        with TestClient(app) as client:
            response = client.get("/performance")

        assert response.status_code == 503
        assert response.json()["error"] == "database_unavailable"
