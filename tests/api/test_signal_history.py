"""Testes de histórico de sinais (SPEC_025)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.signals import router


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


class TestSignalHistoryEndpoint:
    def test_retorna_200_com_ate_50_sinais(self) -> None:
        signals = [
            {
                "symbol": "BTCUSDT",
                "timeframe": "15m",
                "direction": "LONG",
                "entry_price": 80000.0,
                "stop_loss": 79500.0,
                "take_profit": 81000.0,
                "risk_reward_ratio": 2.0,
                "detected_at": datetime(2026, 5, 8, 12, 0, tzinfo=UTC),
                "execution_status": "REJECTED_RISK_MAX_CAPITAL",
                "execution_reason": "max_capital_allocation_exceeded",
                "outcome_at": datetime(2026, 5, 8, 12, 0, 1, tzinfo=UTC),
            }
            for _ in range(50)
        ]
        repo = AsyncMock()
        repo.get_signal_history = AsyncMock(return_value=signals)

        app = _make_app(repo=repo)
        with TestClient(app) as client:
            response = client.get("/signals/history")

        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 50
        assert len(payload["signals"]) == 50
        assert payload["signals"][0]["detected_at"].endswith("Z")
        assert payload["signals"][0]["outcome_at"].endswith("Z")
        assert payload["signals"][0]["detected_at_br"] == "08/05/2026 09:00:00"
        assert payload["signals"][0]["outcome_at_br"] == "08/05/2026 09:00:01"
        assert payload["generated_at_br"]
        assert payload["timezone"] == "America/Sao_Paulo"
        repo.get_signal_history.assert_awaited_once_with(limit=50)

    def test_legado_sem_status_recebe_unknown_legacy(self) -> None:
        repo = AsyncMock()
        repo.get_signal_history = AsyncMock(
            return_value=[
                {
                    "symbol": "ETHUSDT",
                    "timeframe": "15m",
                    "direction": "SHORT",
                    "detected_at": datetime(2026, 5, 8, 11, 0, tzinfo=UTC),
                }
            ]
        )

        app = _make_app(repo=repo)
        with TestClient(app) as client:
            response = client.get("/signals/history")

        assert response.status_code == 200
        signal = response.json()["signals"][0]
        assert signal["execution_status"] == "UNKNOWN_LEGACY"
        assert signal["execution_reason"] == "causa indisponível (pré-rastreio)"
        assert signal["detected_at_br"] == "08/05/2026 08:00:00"

    def test_retorna_503_sem_repositorio(self) -> None:
        app = _make_app(repo=None)
        with TestClient(app) as client:
            response = client.get("/signals/history")

        assert response.status_code == 503
        assert response.json() == {"detail": "Repositório indisponível"}

    def test_retorna_503_quando_repositorio_falha(self) -> None:
        repo = AsyncMock()
        repo.get_signal_history = AsyncMock(side_effect=RuntimeError("db down"))

        app = _make_app(repo=repo)
        with TestClient(app) as client:
            response = client.get("/signals/history")

        assert response.status_code == 503
        assert response.json() == {"detail": "Repositório indisponível"}

    def test_diagnosis_retorna_200_com_payload(self) -> None:
        repo = AsyncMock()
        repo.get_signal_generation_diagnosis = AsyncMock(
            return_value={
                "symbol": "PLTRUSDT",
                "timeframe": "15m",
                "classification": "REJECTED_BY_RISK",
                "last_evidence_at": datetime(2026, 5, 13, 14, 31, 5, tzinfo=UTC),
                "risk_reason": "quantity_zero_after_rounding",
                "engine_outcome": "signal_detected",
                "engine_reason": "checklist_not_satisfied:ao_confirmed",
                "reason": "conditions_not_met",
                "rule_hits": ["RN-PHI-005:consolidation", "RN-PHI-024:chart_confirmed"],
                "phicube_mode": "shadow",
                "explicacao_humana": "Mercado lateral, sem direção clara para entrada segura.",
                "risk_outcome": "rejected",
                "details": {
                    "candle_close_time": "2026-05-13T14:30:00Z",
                    "engine_reason": "checklist_not_satisfied:ao_confirmed",
                    "market_state": "consolidation",
                },
            }
        )

        app = _make_app(repo=repo)
        with TestClient(app) as client:
            response = client.get("/signals/diagnosis/pltrusdt/15m")

        assert response.status_code == 200
        payload = response.json()
        assert payload["classification"] == "REJECTED_BY_RISK"
        assert payload["engine_reason"] == "checklist_not_satisfied:ao_confirmed"
        assert payload["reason"] == "conditions_not_met"
        assert payload["rule_hits"] == ["RN-PHI-005:consolidation", "RN-PHI-024:chart_confirmed"]
        assert payload["phicube_mode"] == "shadow"
        assert "lateral" in payload["explicacao_humana"]
        assert payload["details"]["market_state"] == "consolidation"
        assert payload["last_evidence_at"].endswith("Z")
        assert payload["last_evidence_at_br"] == "13/05/2026 11:31:05"
        repo.get_signal_generation_diagnosis.assert_awaited_once_with(
            symbol="PLTRUSDT",
            timeframe="15m",
        )


class TestSignalHistoryRepository:
    @pytest.mark.asyncio
    async def test_get_signal_history_ordena_por_detected_at_desc(self) -> None:
        repo = _make_repo()
        returned = [{"symbol": "BTCUSDT"}, {"symbol": "ETHUSDT"}]
        aggregate_cursor = AsyncMock()
        aggregate_cursor.to_list = AsyncMock(return_value=returned)
        collection = MagicMock()
        collection.aggregate = MagicMock(return_value=aggregate_cursor)
        repo._db = MagicMock()
        repo._db.__getitem__ = MagicMock(return_value=collection)

        result = await repo.get_signal_history(limit=50)

        assert result == returned
        pipeline = collection.aggregate.call_args.args[0]
        assert pipeline[0] == {"$sort": {"detected_at": -1}}
        assert pipeline[1] == {"$limit": 50}
        assert pipeline[2]["$project"]["execution_status"] == 1
        assert pipeline[2]["$project"]["execution_reason"] == 1

    @pytest.mark.asyncio
    async def test_update_signal_execution_outcome_grava_status(self) -> None:
        repo = _make_repo()
        collection = AsyncMock()
        collection.update_one = AsyncMock(return_value=MagicMock(matched_count=1))
        repo._db = MagicMock()
        repo._db.__getitem__ = MagicMock(return_value=collection)

        updated = await repo.update_signal_execution_outcome(
            "681cc200e8f9ff89bff8e463",
            execution_status="REJECTED_ORDER_EXECUTION",
            execution_reason="order_manager_execute_returned_none",
            execution_details={"attempt": 1},
        )

        assert updated is True
        query = collection.update_one.call_args.args[0]
        update = collection.update_one.call_args.args[1]
        assert "_id" in query
        assert update["$set"]["execution_status"] == "REJECTED_ORDER_EXECUTION"
        assert update["$set"]["execution_reason"] == "order_manager_execute_returned_none"

    @pytest.mark.asyncio
    async def test_get_latest_signal_diagnostics_agrega_por_symbol_timeframe(self) -> None:
        repo = _make_repo()
        returned = [{"symbol": "BTCUSDT", "timeframe": "15m", "decision": "NO_SIGNAL"}]
        aggregate_cursor = AsyncMock()
        aggregate_cursor.to_list = AsyncMock(return_value=returned)
        collection = MagicMock()
        collection.aggregate = MagicMock(return_value=aggregate_cursor)
        repo._db = MagicMock()
        repo._db.__getitem__ = MagicMock(return_value=collection)

        result = await repo.get_latest_signal_diagnostics(limit=10)

        assert result == returned
        pipeline = collection.aggregate.call_args.args[0]
        assert pipeline[0] == {"$match": {"event": "signal_evaluated"}}
        assert pipeline[1] == {"$sort": {"ts": -1}}

    @pytest.mark.asyncio
    async def test_get_signal_generation_diagnosis_sem_evento_retorna_pipeline_interrupted(
        self,
    ) -> None:
        repo = _make_repo()
        audit_col = MagicMock()
        audit_col.find_one = AsyncMock(
            side_effect=[None, {"ts": datetime(2026, 5, 13, tzinfo=UTC)}]
        )
        repo._db = MagicMock()
        repo._db.__getitem__ = MagicMock(return_value=audit_col)

        result = await repo.get_signal_generation_diagnosis("PLTRUSDT", "15m")

        assert result["classification"] == "PIPELINE_INTERRUPTED"
        assert result["engine_reason"] is None
        assert result["reason"] is None
        assert result["rule_hits"] == []
        assert result["phicube_mode"] == "shadow"
        assert result["explicacao_humana"] is None
        assert result["details"]["reason"] == "no_signal_cycle_diagnostic_event_found"

    @pytest.mark.asyncio
    async def test_get_signal_generation_diagnosis_com_evento_retorna_classificacao(self) -> None:
        repo = _make_repo()
        audit_col = MagicMock()
        audit_col.find_one = AsyncMock(
            return_value={
                "ts": datetime(2026, 5, 13, 14, 31, 5, tzinfo=UTC),
                "final_status": "REJECTED_BY_RISK",
                "risk_reason": "quantity_zero_after_rounding",
                "engine_outcome": "signal_detected",
                "engine_reason": "regime_lateral_blocked",
                "reason": "conditions_not_met",
                "rule_hits": ["RN-PHI-005:consolidation", "RN-PHI-024:chart_confirmed"],
                "phicube_mode": "advisory",
                "explicacao_humana": "Mercado lateral, sem direção clara para entrada segura.",
                "risk_outcome": "rejected",
                "market_state": "consolidation",
                "candle_close_time": "2026-05-13T14:30:00Z",
                "technical_indicators": {
                    "status": "ok",
                    "close": 0.2575,
                    "ma20": 0.2561,
                    "ma50": 0.2554,
                },
            }
        )
        repo._db = MagicMock()
        repo._db.__getitem__ = MagicMock(return_value=audit_col)

        result = await repo.get_signal_generation_diagnosis("PLTRUSDT", "15m")

        assert result["classification"] == "REJECTED_BY_RISK"
        assert result["risk_reason"] == "quantity_zero_after_rounding"
        assert result["engine_reason"] == "regime_lateral_blocked"
        assert result["reason"] == "conditions_not_met"
        assert result["rule_hits"] == ["RN-PHI-005:consolidation", "RN-PHI-024:chart_confirmed"]
        assert result["phicube_mode"] == "advisory"
        assert "lateral" in result["explicacao_humana"]
        assert result["details"]["engine_reason"] == "regime_lateral_blocked"
        assert result["details"]["market_state"] == "consolidation"
        assert result["details"]["technical_indicators"]["status"] == "ok"
