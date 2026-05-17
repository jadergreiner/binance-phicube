"""Testes de contrato para rotas operacionais por símbolo (P0)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.symbols import router as symbols_router


def _app_with_repo(repo: AsyncMock):
    app = FastAPI()
    app.include_router(symbols_router)
    app.state.repository = repo
    app.state.settings = type(
        "Settings",
        (),
        {
            "symbol_timeframes": [
                type("Cfg", (), {"symbol": "BTCUSDT", "timeframe": "15m"})(),
            ]
        },
    )()
    app.state.position_stream = type("Stream", (), {"get_positions": lambda self: []})()
    return app


def test_symbols_overview_retorna_resumo_operacional() -> None:
    repo = AsyncMock()
    repo.get_signal_generation_diagnosis = AsyncMock(
        return_value={
            "classification": "NO_SETUP_DETECTED",
            "risk_reason": None,
            "engine_outcome": "no_signal",
            "last_evidence_at": datetime.now(UTC),
        }
    )
    app = _app_with_repo(repo)
    with TestClient(app) as client:
        response = client.get("/symbols/overview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    row = payload["symbols"][0]
    assert row["symbol"] == "BTCUSDT"
    assert row["timeframe"] == "15m"
    assert "risk_status" in row
    assert "as_of" in row
    assert set(("symbols", "total", "generated_at", "generated_at_br", "timezone")).issubset(
        payload.keys()
    )


def test_symbol_detail_retorna_facade_com_explicacao_humana() -> None:
    repo = AsyncMock()
    repo.get_signal_generation_diagnosis = AsyncMock(
        return_value={
            "classification": "NO_SETUP_DETECTED",
            "risk_reason": None,
            "engine_outcome": "no_signal",
            "last_evidence_at": datetime.now(UTC),
        }
    )
    repo.get_trade_history = AsyncMock(return_value=[])
    app = _app_with_repo(repo)
    with TestClient(app) as client:
        response = client.get("/symbols/BTCUSDT/detail?timeframe=15m")
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "BTCUSDT"
    assert payload["timeframe"] == "15m"
    assert "snapshot" in payload
    assert "risk" in payload
    assert "last_analysis" in payload
    assert "chart" in payload
    assert "trades_history" in payload
    assert set(("snapshot", "risk", "last_analysis", "chart", "trades_history")).issubset(
        payload.keys()
    )
    human = payload["last_analysis"]["human_explanation"]
    assert all(
        k in human for k in ("what_i_saw", "what_i_decided", "why", "next_step", "full_text")
    )
    assert "technical_explanation" in payload["last_analysis"]
    assert "technical_explanation_structured" in payload["last_analysis"]


def test_symbol_detail_enriquece_explicacao_tecnica_com_medias_e_estocastico() -> None:
    repo = AsyncMock()
    repo.get_signal_generation_diagnosis = AsyncMock(
        return_value={
            "classification": "NO_SETUP_DETECTED",
            "risk_reason": None,
            "engine_outcome": "no_signal",
            "last_evidence_at": datetime.now(UTC),
            "details": {
                "technical_indicators": {
                    "status": "ok",
                    "close": 0.2575,
                    "ma20": 0.2561,
                    "ma50": 0.2554,
                    "price_vs_ma20_pct": 0.5466,
                    "price_vs_ma50_pct": 0.8222,
                    "price_above_ma20": True,
                    "price_above_ma50": True,
                    "ma_alignment": "bullish",
                    "stoch_k": 78.11,
                    "stoch_d": 73.52,
                    "stoch_zone": "neutral",
                    "stoch_signal": "k_above_d",
                }
            },
        }
    )
    repo.get_trade_history = AsyncMock(return_value=[])
    app = _app_with_repo(repo)
    with TestClient(app) as client:
        response = client.get("/symbols/BTCUSDT/detail?timeframe=15m")

    assert response.status_code == 200
    technical = response.json()["last_analysis"]["technical_explanation_structured"]
    assert "SMA20=" in technical["medias"]
    assert "SMA50=" in technical["medias"]
    assert "K=78.11" in technical["oscilador"]
    assert "D=73.52" in technical["oscilador"]
