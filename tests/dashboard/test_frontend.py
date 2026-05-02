"""Testes unitários do frontend estático do dashboard de posições."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.api import main as api_main


ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = ROOT / "src" / "frontend" / "static" / "index.html"
APP_JS = ROOT / "src" / "frontend" / "static" / "app.js"


def test_frontend_nao_depende_de_cdn_externo() -> None:
    """O HTML não pode carregar scripts ou estilos de CDN."""
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert "https://" not in html
    assert "http://" not in html
    assert "/static/app.js" in html
    assert "/static/style.css" in html


def test_frontend_e_somente_leitura_e_consumidor_de_websocket() -> None:
    """A UI não pode expor ações de trade e deve consumir /ws/positions."""
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "/ws/positions" in javascript
    assert "open position" not in javascript.lower()
    assert "close position" not in javascript.lower()
    assert "take profit" not in javascript.lower()
    assert "stop loss" not in javascript.lower()


def test_get_root_entrega_o_frontend_estatico(monkeypatch) -> None:
    """GET / deve servir a página principal do frontend estático."""
    monkeypatch.setattr(
        api_main,
        "get_settings",
        lambda: SimpleNamespace(
            dashboard_api_key="dash_key",
            dashboard_api_secret="dash_secret",
            binance_testnet=True,
        ),
    )
    monkeypatch.setattr(api_main.DashboardClient, "connect", AsyncMock(return_value=None))
    monkeypatch.setattr(api_main.DashboardClient, "close", AsyncMock(return_value=None))
    monkeypatch.setattr(api_main.PositionStream, "start", AsyncMock(return_value=None))
    monkeypatch.setattr(api_main.PositionStream, "stop", AsyncMock(return_value=None))
    monkeypatch.setattr(api_main.AdaptiveUpdater, "start", AsyncMock(return_value=None))
    monkeypatch.setattr(api_main.AdaptiveUpdater, "stop", AsyncMock(return_value=None))

    with TestClient(api_main.create_app()) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Consulta de Posições" in response.text