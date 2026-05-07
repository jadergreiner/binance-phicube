"""Testes de atividade do bot (SPEC_016)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.health import router


def _make_app(repo=None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    if repo is not None:
        app.state.repository = repo
    return app


def _make_repo():
    with patch("motor.motor_asyncio.AsyncIOMotorClient"):
        from src.storage.repository import MongoRepository

        return MongoRepository("mongodb://localhost/test", "test_db")


class TestBotActivityEndpoint:
    def test_retorna_active_quando_atividade_recente(self) -> None:
        repo = AsyncMock()
        repo.get_last_bot_activity_at = AsyncMock(
            return_value=datetime.now(UTC) - timedelta(minutes=5)
        )
        app = _make_app(repo=repo)

        with TestClient(app) as client:
            response = client.get("/bot-activity")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "active"
        assert payload["threshold_minutes"] == 10
        assert payload["minutes_since_last_activity"] <= 10
        assert payload["last_activity_at"] is not None

    def test_retorna_inactive_quando_atividade_antiga(self) -> None:
        repo = AsyncMock()
        repo.get_last_bot_activity_at = AsyncMock(
            return_value=datetime.now(UTC) - timedelta(minutes=11)
        )
        app = _make_app(repo=repo)

        with TestClient(app) as client:
            response = client.get("/bot-activity")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "inactive"
        assert payload["minutes_since_last_activity"] > 10

    def test_retorna_inactive_sem_documentos(self) -> None:
        repo = AsyncMock()
        repo.get_last_bot_activity_at = AsyncMock(return_value=None)
        app = _make_app(repo=repo)

        with TestClient(app) as client:
            response = client.get("/bot-activity")

        assert response.status_code == 200
        assert response.json()["status"] == "inactive"
        assert response.json()["last_activity_at"] is None
        assert response.json()["minutes_since_last_activity"] is None

    def test_retorna_200_mesmo_com_falha_mongodb(self) -> None:
        repo = AsyncMock()
        repo.get_last_bot_activity_at = AsyncMock(side_effect=RuntimeError("boom"))
        app = _make_app(repo=repo)

        with TestClient(app) as client:
            response = client.get("/bot-activity")

        assert response.status_code == 200
        assert response.json()["status"] == "inactive"
        assert response.json()["last_activity_at"] is None


class TestBotActivityRepository:
    @pytest.mark.asyncio
    async def test_usa_documento_mais_recente_entre_signals_e_audit(self) -> None:
        repo = _make_repo()
        newer = ObjectId()
        older = ObjectId.from_datetime(datetime.now(UTC) - timedelta(minutes=15))

        signals_collection = AsyncMock()
        signals_collection.find_one = AsyncMock(return_value={"_id": older})
        audit_collection = AsyncMock()
        audit_collection.find_one = AsyncMock(return_value={"_id": newer})

        repo._db = MagicMock()
        repo._db.__getitem__ = MagicMock(
            side_effect=lambda name: {
                "signals": signals_collection,
                "audit": audit_collection,
            }[name]
        )

        last_activity = await repo.get_last_bot_activity_at()

        assert last_activity is not None
        assert last_activity == newer.generation_time.astimezone(UTC)
