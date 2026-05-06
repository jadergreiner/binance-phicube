"""Testes para GET /performance/by-symbol e GET /performance/by-timeframe (SPEC_009)."""
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


def _mock_repo_by_symbol():
    mock_repo = AsyncMock()
    mock_repo.get_performance_by_symbol = AsyncMock(
        return_value={
            "BTCUSDT": {
                "total_trades": 5,
                "win_rate_pct": 60.0,
                "total_pnl_usdt": 42.0,
                "avg_rrr": 1.8,
                "max_drawdown_usdt": -10.0,
                "profit_factor": 2.5,
            },
            "ETHUSDT": {
                "total_trades": 3,
                "win_rate_pct": 33.33,
                "total_pnl_usdt": -5.0,
                "avg_rrr": 0.9,
                "max_drawdown_usdt": -15.0,
                "profit_factor": 0.5,
            },
        }
    )
    return mock_repo


def _mock_repo_by_timeframe():
    mock_repo = AsyncMock()
    mock_repo.get_performance_by_timeframe = AsyncMock(
        return_value={
            "4h": {
                "total_trades": 6,
                "win_rate_pct": 50.0,
                "total_pnl_usdt": 10.0,
                "avg_rrr": 1.2,
                "max_drawdown_usdt": -8.0,
                "profit_factor": 1.5,
            },
            "1d": {
                "total_trades": 2,
                "win_rate_pct": 100.0,
                "total_pnl_usdt": 37.0,
                "avg_rrr": 3.0,
                "max_drawdown_usdt": 0.0,
                "profit_factor": 0.0,
            },
        }
    )
    return mock_repo


class TestPerformanceBySymbolEndpoint:
    """TEST_009_05 — GET /performance/by-symbol."""

    def test_retorna_200_com_metricas_por_simbolo(self) -> None:
        """TEST_009_05: endpoint retorna 200 com by_symbol e generated_at."""
        app = _make_app(repo=_mock_repo_by_symbol())

        with TestClient(app) as client:
            response = client.get("/performance/by-symbol")

        assert response.status_code == 200
        data = response.json()
        assert "by_symbol" in data
        assert "generated_at" in data
        assert "BTCUSDT" in data["by_symbol"]
        assert "ETHUSDT" in data["by_symbol"]
        assert data["by_symbol"]["BTCUSDT"]["total_trades"] == 5
        assert data["by_symbol"]["ETHUSDT"]["win_rate_pct"] == 33.33

    def test_retorna_503_sem_repositorio(self) -> None:
        """TEST_009_07 (by-symbol): repositório ausente → 503."""
        app = _make_app(repo=None)

        with TestClient(app) as client:
            response = client.get("/performance/by-symbol")

        assert response.status_code == 503
        assert response.json()["error"] == "database_unavailable"


class TestPerformanceByTimeframeEndpoint:
    """TEST_009_06 — GET /performance/by-timeframe."""

    def test_retorna_200_com_metricas_por_timeframe(self) -> None:
        """TEST_009_06: endpoint retorna 200 com by_timeframe e generated_at."""
        app = _make_app(repo=_mock_repo_by_timeframe())

        with TestClient(app) as client:
            response = client.get("/performance/by-timeframe")

        assert response.status_code == 200
        data = response.json()
        assert "by_timeframe" in data
        assert "generated_at" in data
        assert "4h" in data["by_timeframe"]
        assert "1d" in data["by_timeframe"]
        assert data["by_timeframe"]["4h"]["total_trades"] == 6
        assert data["by_timeframe"]["1d"]["win_rate_pct"] == 100.0

    def test_retorna_503_sem_repositorio(self) -> None:
        """TEST_009_07 (by-timeframe): repositório ausente → 503."""
        app = _make_app(repo=None)

        with TestClient(app) as client:
            response = client.get("/performance/by-timeframe")

        assert response.status_code == 503
        assert response.json()["error"] == "database_unavailable"
