"""Testes unitários do frontend estático do dashboard de posições."""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.api import main as api_main

ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = ROOT / "src" / "frontend" / "static" / "index.html"
APP_JS = ROOT / "src" / "frontend" / "static" / "app.js"
STYLE_CSS = ROOT / "src" / "frontend" / "static" / "style.css"


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
    assert 'id="onboarding-sync-status"' in html
    assert "Gerenciar" in javascript
    assert "/market-analysis" in javascript
    assert 'method: "PATCH"' in javascript
    assert "/backtest-jobs" in javascript
    assert "_pollBacktestJob" in javascript
    assert "consistency_status" in javascript
    assert "renderOnboardingSyncStatus" in javascript
    assert "/onboarding/${symbol}/backtest`" not in javascript


def test_frontend_onboarding_defaults_padronizados() -> None:
    """Onboarding deve iniciar com defaults COPPERUSDT, 1h e 10x."""
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert 'id="ob-symbol"' in html
    assert 'placeholder="COPPERUSDT"' in html
    assert 'value="COPPERUSDT"' in html
    assert '<option value="1h" selected>1h</option>' in html
    assert 'id="ob-leverage"' in html
    assert 'value="10"' in html


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
    assert "ENTRY_OPEN_NO_PROTECTION" in javascript


def test_frontend_expoe_diagnostico_de_sinais_em_tempo_real() -> None:
    """Diagnóstico de sinais deve existir no HTML e ser renderizado via snapshot."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "Diagnóstico de Sinais" in html
    assert 'id="signal-diagnostic-body"' in html
    assert "renderSignalTelemetry" in javascript
    assert "snapshot.signal_telemetry" in javascript


def test_frontend_expoe_comparativo_de_bias_views() -> None:
    """Dashboard deve exibir seletor, divergência e métricas das visões de bias."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    javascript = APP_JS.read_text(encoding="utf-8")

    assert 'id="analysis-bias-view"' in html
    assert 'id="analysis-bias-divergence"' in html
    assert 'id="analysis-bias-metrics"' in html
    assert "renderBiasViews" in javascript
    assert "analysis?.bias_views" in javascript


def test_frontend_prioriza_campos_br_com_fallback_legado() -> None:
    """SPEC_026 — horários devem priorizar *_br com fallback para campos ISO antigos."""
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "getDateTimeLabel" in javascript
    assert "getClockTimeLabel" in javascript
    assert "_br" in javascript


def test_frontend_expoe_controles_v2_de_ordenacao_e_highlights() -> None:
    """Dashboard V2 deve permitir reordenação e exibir highlights de símbolos/trades."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    javascript = APP_JS.read_text(encoding="utf-8")

    assert 'id="sort-key"' in html
    assert 'id="sort-dir"' in html
    assert 'id="save-view-btn"' in html
    assert 'id="top-symbols-profitable"' in html
    assert 'id="top-symbols-losing"' in html
    assert 'id="best-trade"' in html
    assert 'id="worst-trade"' in html
    assert "POSITION_VIEW_STORAGE_KEY" in javascript
    assert "persistPositionViewPreference" in javascript
    assert "restorePositionViewPreference" in javascript
    assert "unrealized_pnl_usdt" in javascript
    assert "quantity" in javascript


def test_frontend_expoe_secao_assertividade_modelos() -> None:
    """Dashboard deve expor seção de assertividade por símbolo/período."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "Assertividade dos Modelos" in html
    assert 'id="assertiveness-symbol"' in html
    assert 'id="assertiveness-timeframe"' in html
    assert 'id="assertiveness-period"' in html
    assert 'id="assertiveness-start"' in html
    assert 'id="assertiveness-end"' in html
    assert "assertiveness-filters" in html
    assert 'id="assertiveness-ranking-body"' in html
    assert 'id="assertiveness-timeline-body"' in html
    assert "/performance/assertiveness" in javascript
    assert "fetchAssertiveness" in javascript
    assert "syncAssertivenessCustomControls" in javascript


def test_frontend_expoe_navegacao_por_abas() -> None:
    """Onda A: frontend canônico deve expor navegação por abas."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "tabs-nav" in html
    assert 'data-tab="overview"' in html
    assert 'data-tab="positions"' in html
    assert 'data-tab="signals"' in html
    assert 'data-tab="onboarding"' in html
    assert "bindTabEvents" in javascript
    assert "applyActiveTab" in javascript


def test_frontend_onda_b_reorganiza_blocos_operacionais_por_aba() -> None:
    """Onda B: blocos operacionais devem estar distribuídos por abas sem perder IDs."""
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert 'data-tab="positions"' in html
    assert 'data-tab="signals"' in html
    assert 'id="positions-body"' in html
    assert 'id="open-trades-body"' in html
    assert 'id="trade-history-body"' in html
    assert 'id="signal-history-body"' in html


def test_frontend_symbols_overview_expoe_filtros_ordenacao_e_persistencia() -> None:
    """P1: overview de símbolos deve expor filtros/sort e persistir preferência local."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    javascript = APP_JS.read_text(encoding="utf-8")

    assert 'id="symbols-overview-filter-risk"' in html
    assert 'id="symbols-overview-filter-symbol"' in html
    assert 'id="symbols-overview-sort-key"' in html
    assert 'id="symbols-overview-sort-dir"' in html
    assert 'id="symbols-overview-sort-chip"' in html
    assert 'id="symbols-overview-clear-filters"' in html
    assert 'id="symbols-overview-count-ok"' in html
    assert 'id="symbols-overview-count-atencao"' in html
    assert 'id="symbols-overview-count-bloqueado"' in html
    assert 'id="symbols-detail-analyzed-at-value"' in html
    assert 'id="symbols-detail-technical-value"' in html
    assert "SYMBOLS_OVERVIEW_VIEW_STORAGE_KEY" in javascript
    assert "persistSymbolsOverviewPreference" in javascript
    assert "restoreSymbolsOverviewPreference" in javascript
    assert "applySymbolsOverviewFiltersAndSort" in javascript
    assert "renderSymbolsOverviewSortChip" in javascript
    assert "Ordenado por:" in javascript
    assert "symbolsOverviewCountOk" in javascript
    assert "symbolsOverviewCountAtencao" in javascript
    assert "symbolsOverviewCountBloqueado" in javascript
    assert "toggleRiskFilter" in javascript
    assert 'toggleRiskFilter("ok")' in javascript
    assert 'toggleRiskFilter("atencao")' in javascript
    assert 'toggleRiskFilter("bloqueado")' in javascript


def test_frontend_symbols_overview_renderiza_fallback_quando_filtro_zera_resultado() -> None:
    """P1: fallback de render deve informar ausência de dados para o filtro aplicado."""
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "Sem dados para o filtro aplicado." in javascript


def test_frontend_detail_mapeia_novos_motivos_de_rejeicao_do_signal_engine() -> None:
    """Detail do símbolo deve traduzir motivos de gate de regime/checklist."""
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "formatSignalEngineReason" in javascript
    assert "regime lateral bloqueado" in javascript
    assert "checklist BO Williams incompleto" in javascript
    assert 'decision === "NO_SETUP_DETECTED"' in javascript


def test_frontend_detail_expoe_comparacao_bo_vs_ml() -> None:
    """Detalhe do símbolo deve exibir comparação BO vs ML no painel operacional."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "Comparação BO vs ML" in html
    assert 'id="symbols-detail-ml-comparison-value"' in html
    assert "symbolsDetailMlComparisonValue" in javascript
    assert "ML inativo" in javascript
    assert "BO=${decision}; ML=${mlDecision}" in javascript


def test_frontend_symbols_overview_expoe_estado_visual_ativo_no_badge_de_risco() -> None:
    """Badge de risco selecionado deve ter estado visual ativo para feedback imediato."""
    javascript = APP_JS.read_text(encoding="utf-8")
    css = STYLE_CSS.read_text(encoding="utf-8")

    assert "renderSymbolsOverviewRiskBadgeState" in javascript
    assert "risk-badge-active" in javascript
    assert "aria-pressed" in javascript
    assert ".risk-badge-active" in css


def test_frontend_symbols_overview_badges_expoem_aria_pressed() -> None:
    """Badges de risco devem expor aria-pressed para estado semântico acessível."""
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert 'id="symbols-overview-count-ok"' in html
    assert 'id="symbols-overview-count-atencao"' in html
    assert 'id="symbols-overview-count-bloqueado"' in html
    assert 'aria-pressed="false"' in html


def test_frontend_symbols_overview_expoe_regiao_aria_live_para_filtros() -> None:
    """Overview deve anunciar mudanças de filtro para tecnologia assistiva."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    javascript = APP_JS.read_text(encoding="utf-8")
    css = STYLE_CSS.read_text(encoding="utf-8")

    assert 'id="symbols-overview-live-region"' in html
    assert 'aria-live="polite"' in html
    assert "announceLiveRegion" in javascript
    assert ".sr-only" in css


def test_frontend_positions_e_assertividade_expoem_aria_live_para_filtros() -> None:
    """Posições e assertividade devem expor anúncio assistivo de mudanças de filtro."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    javascript = APP_JS.read_text(encoding="utf-8")

    assert 'id="positions-live-region"' in html
    assert 'id="assertiveness-live-region"' in html
    assert "announceLiveRegion(elements.positionsLiveRegion" in javascript
    assert "elements.assertivenessLiveRegion" in javascript


def test_frontend_expoe_constante_a11y_messages_com_chaves_minimas() -> None:
    """A11Y_MESSAGES deve existir com blocos mínimos para anúncios assistivos."""
    javascript = APP_JS.read_text(encoding="utf-8")

    assert "const A11Y_MESSAGES =" in javascript
    assert "symbols:" in javascript
    assert "positions:" in javascript
    assert "assertiveness:" in javascript
    assert "riskApplied" in javascript
    assert "viewSaved" in javascript
    assert "periodChanged" in javascript


def test_frontend_announce_live_region_nao_aceita_mensagem_hardcoded_fora_a11y_messages() -> None:
    """announceLiveRegion deve receber mensagens vindas de A11Y_MESSAGES, não strings inline."""
    javascript = APP_JS.read_text(encoding="utf-8")
    match = re.search(r"const A11Y_MESSAGES\s*=\s*\{", javascript)
    assert match is not None
    tail = javascript[match.end() :]

    hardcoded_quote = re.findall(r"announceLiveRegion\([^)]*,\s*['\"][^'\"]+['\"]\)", tail)
    hardcoded_template = re.findall(r"announceLiveRegion\([^)]*,\s*`[^`]+`\)", tail)

    assert not hardcoded_quote, f"Mensagens hardcoded detectadas: {hardcoded_quote}"
    assert not hardcoded_template, f"Mensagens hardcoded detectadas: {hardcoded_template}"


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
