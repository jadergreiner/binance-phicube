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


def test_frontend_nao_inferir_degraded_por_idade_local() -> None:
    """A UI não deve deduzir degradado por watchdog/timeout local."""
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "REFRESH_THRESHOLD_MS" not in javascript
    assert "WATCHDOG_INTERVAL_MS" not in javascript
    assert "checkRefreshState" not in javascript
    assert "startWatchdog" not in javascript
    assert "lastSnapshotReceivedAt" not in javascript


def test_frontend_prioriza_status_vindo_do_backend() -> None:
    """O status renderizado deve vir do snapshot retornado pelo backend."""
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "setStatus(snapshot.status);" in javascript
    assert "setBanner(snapshot.banner);" in javascript


def test_frontend_expoe_gestao_de_simbolo_aprovado() -> None:
    """SPEC_024 — sessão aprovada deve oferecer ação de gestão e análise técnica."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "Gestão do Símbolo" in html
    assert "Gerenciar" in javascript
    assert "/market-analysis" in javascript
    assert 'method: "PATCH"' in javascript


def test_frontend_historico_expoe_origem_e_status_reconciliado() -> None:
    """SPEC_024/SPEC_016 — histórico deve explicar fechamento externo reconcilado."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "<th>Origem</th>" in html
    assert "CLOSED_EXTERNAL" in javascript
    assert "Reconciliação externa" in javascript


def test_frontend_expoe_secao_de_sinais_gerados() -> None:
    """SPEC_025 — dashboard exibe sinais detectados e consome endpoint dedicado."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "<h2>Sinais Gerados</h2>" in html
    assert 'id="signal-history-body"' in html
    assert "/signals/history" in javascript
    assert "UNKNOWN_LEGACY" in javascript


def test_frontend_expoe_diagnostico_de_sinais_em_tempo_real() -> None:
    """Diagnóstico de sinais deve existir no HTML e ser renderizado via snapshot."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "Diagnóstico de Sinais" in html
    assert 'id="signal-diagnostic-body"' in html
    assert "renderSignalTelemetry" in javascript
    assert "snapshot.signal_telemetry" in javascript


def test_frontend_prioriza_campos_br_com_fallback_legado() -> None:
    """SPEC_026 — horários devem priorizar *_br com fallback para campos ISO antigos."""
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "getDateTimeLabel" in javascript
    assert "getClockTimeLabel" in javascript
    assert "_br" in javascript


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
