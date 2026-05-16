"""Testes para GET /performance/assertiveness."""

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


def test_assertiveness_retorna_200_com_payload() -> None:
    repo = AsyncMock()
    repo.get_signals_in_period = AsyncMock(return_value=[{"symbol": "BTCUSDT"}])
    repo.get_closed_trades_in_period = AsyncMock(
        return_value=[{"symbol": "BTCUSDT", "pnl_usdt": 10.0, "risk_amount": 5.0}]
    )
    app = _make_app(repo=repo)

    with TestClient(app) as client:
        response = client.get("/performance/assertiveness?period=30d&order_by=pnl_usdt")

    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "ranking" in data
    assert "timeline" in data
    assert data["timezone"] == "America/Sao_Paulo"
    assert data["summary"]["total_signals"] == 1
    assert data["summary"]["total_trades"] == 1


def test_assertiveness_retorna_422_periodo_invalido() -> None:
    repo = AsyncMock()
    app = _make_app(repo=repo)

    with TestClient(app) as client:
        response = client.get("/performance/assertiveness?period=abc")

    assert response.status_code == 422
    assert response.json()["error"] == "invalid_period"


def test_assertiveness_retorna_503_sem_repositorio() -> None:
    app = _make_app(repo=None)
    with TestClient(app) as client:
        response = client.get("/performance/assertiveness")

    assert response.status_code == 503
    assert response.json()["error"] == "database_unavailable"
