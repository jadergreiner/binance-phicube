"""Testes dos endpoints de onboarding de símbolo (SPEC_019).

TEST_019_01: criar sessão candidata com parâmetros válidos
TEST_019_02: rejeitar símbolo já ativo no bot
TEST_019_03: rejeitar sessão duplicada para mesmo símbolo
TEST_019_04: backtest transiciona para BACKTESTED com métricas
TEST_019_05: aprovar sessão BACKTESTED gera config_string
TEST_019_06: config_string no formato correto SYMBOL:TIMEFRAME:LEVERAGE
TEST_019_07: listar sessões retorna lista
TEST_019_08: deletar sessão remove do banco
TEST_019_09: aprovar sessão não-BACKTESTED retorna 409
TEST_019_10: backtest em sessão inexistente retorna 404
"""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.onboarding import router

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_app(
    sessions: list[dict] | None = None,
    active_symbols: set[str] | None = None,
    *,
    auth_required: bool = False,
    auth_token: str | None = None,
):
    app = FastAPI()
    app.include_router(router)

    repo = AsyncMock()
    _sessions: dict[str, dict] = {}
    if sessions:
        for s in sessions:
            _sessions[s["symbol"]] = s

    async def _get(symbol: str):
        return _sessions.get(symbol)

    async def _list():
        return list(_sessions.values())

    async def _create(doc: dict):
        _sessions[doc["symbol"]] = dict(doc)

    async def _update(symbol: str, update: dict):
        if symbol in _sessions:
            _sessions[symbol].update(update)
            _sessions[symbol]["updated_at"] = datetime.now(UTC)

    async def _delete(symbol: str) -> bool:
        if symbol in _sessions:
            del _sessions[symbol]
            return True
        return False

    repo.get_onboarding_session = _get
    repo.list_onboarding_sessions = _list
    repo.create_onboarding_session = _create
    repo.update_onboarding_session = _update
    repo.delete_onboarding_session = _delete

    app.state.repository = repo

    settings = MagicMock()
    cfg_list = []
    for sym in (active_symbols or {"BTCUSDT", "ETHUSDT"}):
        c = MagicMock()
        c.symbol = sym
        cfg_list.append(c)
    settings.symbol_timeframes = cfg_list
    settings.dashboard_write_auth_required = auth_required
    settings.dashboard_write_auth_token = auth_token
    app.state.settings = settings

    return app, _sessions


def _session(symbol: str = "ATOMUSDT", status: str = "CANDIDATE") -> dict:
    now = datetime.now(UTC)
    return {
        "symbol": symbol,
        "timeframe": "15m",
        "leverage": 3,
        "status": status,
        "created_at": now,
        "updated_at": now,
        "backtest_result": None,
        "backtest_limit": None,
        "backtest_error": None,
        "config_string": None,
        "notes": None,
    }


def _backtested_session(symbol: str = "ATOMUSDT") -> dict:
    s = _session(symbol, status="BACKTESTED")
    s["backtest_result"] = {
        "total_trades": 119,
        "win_rate_pct": 40.34,
        "profit_factor": 1.23,
        "max_drawdown_usdt": -396.23,
        "total_pnl_usdt": 339.20,
        "avg_rrr": 1.2,
        "candles_used": 34800,
        "generated_at": datetime.now(UTC).isoformat(),
        "trades": [],
    }
    s["backtest_limit"] = 35000
    return s


# ─── TEST_019_01: criar sessão candidata ──────────────────────────────────────


class TestCriarSessaoCandidata:
    """TEST_019_01 — POST /onboarding cria sessão com status CANDIDATE."""

    def test_criar_sessao_candidata(self) -> None:
        app, store = _make_app()
        client = TestClient(app)

        resp = client.post(
            "/onboarding", json={"symbol": "ATOMUSDT", "timeframe": "15m", "leverage": 3}
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["symbol"] == "ATOMUSDT"
        assert data["status"] == "CANDIDATE"
        assert data["timeframe"] == "15m"
        assert data["leverage"] == 3
        assert "ATOMUSDT" in store


# ─── TEST_019_02: rejeitar símbolo já ativo ───────────────────────────────────


class TestRejeitarSimboloJaAtivo:
    """TEST_019_02 — símbolo presente em SYMBOL_TIMEFRAMES retorna 409."""

    def test_rejeitar_simbolo_ja_ativo(self) -> None:
        app, _ = _make_app(active_symbols={"BTCUSDT", "ETHUSDT", "ATOMUSDT"})
        client = TestClient(app)

        resp = client.post(
            "/onboarding", json={"symbol": "ATOMUSDT", "timeframe": "15m", "leverage": 3}
        )

        assert resp.status_code == 409
        assert resp.json()["error"] == "simbolo_ja_ativo"


# ─── TEST_019_03: rejeitar sessão duplicada ───────────────────────────────────


class TestRejeitarSessaoDuplicada:
    """TEST_019_03 — sessão já existe para o símbolo retorna 409."""

    def test_rejeitar_sessao_duplicada(self) -> None:
        app, _ = _make_app(sessions=[_session("ATOMUSDT")])
        client = TestClient(app)

        resp = client.post(
            "/onboarding", json={"symbol": "ATOMUSDT", "timeframe": "15m", "leverage": 3}
        )

        assert resp.status_code == 409
        assert resp.json()["error"] == "sessao_ja_existe"


# ─── TEST_019_04: backtest transiciona para BACKTESTED ───────────────────────


class TestBacktestTransiciona:
    """TEST_019_04 — POST /onboarding/{symbol}/backtest → BACKTESTED."""

    def test_backtest_transiciona_para_backtested(self) -> None:
        from datetime import UTC, datetime

        from src.backtest.models import BacktestResult

        app, store = _make_app(sessions=[_session("ATOMUSDT")])
        client = TestClient(app)

        mock_result = BacktestResult(
            symbol="ATOMUSDT",
            timeframe="15m",
            candles_used=34800,
            total_trades=119,
            win_rate_pct=40.34,
            profit_factor=1.23,
            max_drawdown_usdt=-396.23,
            total_pnl_usdt=339.20,
            avg_rrr=1.2,
            generated_at=datetime.now(UTC),
        )

        with (
            patch("src.exchange.binance_client.BinanceClient") as MockClient,
            patch("src.backtest.engine.BacktestEngine") as MockEngine,
            patch("src.config.settings.get_settings"),
        ):
            mock_client_inst = AsyncMock()
            MockClient.return_value = mock_client_inst
            mock_engine_inst = MagicMock()
            mock_engine_inst.run = AsyncMock(return_value=mock_result)
            MockEngine.return_value = mock_engine_inst

            resp = client.post("/onboarding/ATOMUSDT/backtest", json={"limit": 35000})

        assert resp.status_code == 200
        assert store["ATOMUSDT"]["status"] == "BACKTESTED"
        assert store["ATOMUSDT"]["backtest_result"] is not None


# ─── TEST_019_05: aprovação gera config_string ───────────────────────────────


class TestAprovacaoGeraConfig:
    """TEST_019_05 — POST /onboarding/{symbol}/approve → config_string preenchida."""

    def test_aprovar_gera_config_string(self) -> None:
        app, store = _make_app(sessions=[_backtested_session("ATOMUSDT")])
        client = TestClient(app)

        resp = client.post("/onboarding/ATOMUSDT/approve", json={})

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "APPROVED"
        assert data["config_string"] is not None
        assert "ATOMUSDT" in data["config_string"]
        assert "operational_checklist" in data
        assert len(data["operational_checklist"]) == 3


# ─── TEST_019_06: config_string formato correto ───────────────────────────────


class TestConfigStringFormato:
    """TEST_019_06 — config_string = SYMBOL:TIMEFRAME:LEVERAGE."""

    def test_config_string_formato(self) -> None:
        app, _ = _make_app(sessions=[_backtested_session("ATOMUSDT")])
        client = TestClient(app)

        resp = client.post("/onboarding/ATOMUSDT/approve", json={})
        data = resp.json()

        parts = data["config_string"].split(":")
        assert len(parts) == 3
        assert parts[0] == "ATOMUSDT"
        assert parts[1] == "15m"
        assert parts[2] == "3"


# ─── TEST_019_07: listar sessões ──────────────────────────────────────────────


class TestListarSessoes:
    """TEST_019_07 — GET /onboarding retorna lista de sessões."""

    def test_listar_sessoes(self) -> None:
        sessions = [_session("ATOMUSDT"), _session("SOLUSDT")]
        app, _ = _make_app(sessions=sessions)
        client = TestClient(app)

        resp = client.get("/onboarding")

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2
        symbols = {s["symbol"] for s in data}
        assert symbols == {"ATOMUSDT", "SOLUSDT"}


# ─── TEST_019_08: deletar sessão ──────────────────────────────────────────────


class TestDeletarSessao:
    """TEST_019_08 — DELETE /onboarding/{symbol} remove sessão."""

    def test_deletar_sessao(self) -> None:
        app, store = _make_app(sessions=[_session("ATOMUSDT")])
        client = TestClient(app)

        resp = client.delete("/onboarding/ATOMUSDT")

        assert resp.status_code == 204
        assert "ATOMUSDT" not in store

    def test_deletar_sessao_inexistente_retorna_404(self) -> None:
        app, _ = _make_app()
        client = TestClient(app)

        resp = client.delete("/onboarding/NAOEXISTE")

        assert resp.status_code == 404


# ─── TEST_019_09: aprovar não-BACKTESTED retorna 409 ─────────────────────────


class TestAprovarEstadoInvalido:
    """TEST_019_09 — aprovar sessão CANDIDATE retorna 409."""

    def test_aprovar_candidate_retorna_409(self) -> None:
        app, _ = _make_app(sessions=[_session("ATOMUSDT", status="CANDIDATE")])
        client = TestClient(app)

        resp = client.post("/onboarding/ATOMUSDT/approve", json={})

        assert resp.status_code == 409
        assert resp.json()["error"] == "estado_invalido"


# ─── TEST_019_10: backtest em sessão inexistente retorna 404 ─────────────────


class TestBacktestSessaoInexistente:
    """TEST_019_10 — backtest em símbolo sem sessão retorna 404."""

    def test_backtest_sessao_inexistente_retorna_404(self) -> None:
        app, _ = _make_app()
        client = TestClient(app)

        resp = client.post("/onboarding/NAOEXISTE/backtest", json={})

        assert resp.status_code == 404


# ─── Validações de entrada ────────────────────────────────────────────────────


class TestValidacoesEntrada:
    """Validações de symbol, timeframe e leverage."""

    def test_symbol_invalido_retorna_422(self) -> None:
        app, _ = _make_app()
        client = TestClient(app)
        # Symbol sem sufixo USDT — inválido
        resp = client.post(
            "/onboarding", json={"symbol": "ATOMBTC", "timeframe": "15m", "leverage": 3}
        )
        assert resp.status_code == 422

    def test_timeframe_invalido_retorna_422(self) -> None:
        app, _ = _make_app()
        client = TestClient(app)
        resp = client.post(
            "/onboarding", json={"symbol": "ATOMUSDT", "timeframe": "99h", "leverage": 3}
        )
        assert resp.status_code == 422

    def test_leverage_fora_do_range_retorna_422(self) -> None:
        app, _ = _make_app()
        client = TestClient(app)
        resp = client.post(
            "/onboarding", json={"symbol": "ATOMUSDT", "timeframe": "15m", "leverage": 50}
        )
        assert resp.status_code == 422


class TestAutenticacaoEscritaOnboarding:
    """SPEC_020 — auth minima para escrita onboarding."""

    def test_escrita_bypass_quando_auth_nao_requerida(self) -> None:
        app, _ = _make_app(auth_required=False)
        client = TestClient(app)
        resp = client.post(
            "/onboarding", json={"symbol": "ATOMUSDT", "timeframe": "15m", "leverage": 3}
        )
        assert resp.status_code == 201

    def test_escrita_rejeita_sem_bearer_quando_requerida(self) -> None:
        app, _ = _make_app(auth_required=True, auth_token="token123")
        client = TestClient(app)
        resp = client.post(
            "/onboarding", json={"symbol": "ATOMUSDT", "timeframe": "15m", "leverage": 3}
        )
        assert resp.status_code == 401
        assert resp.json()["error"] == "unauthorized"

    def test_escrita_rejeita_bearer_invalido_quando_requerida(self) -> None:
        app, _ = _make_app(auth_required=True, auth_token="token123")
        client = TestClient(app)
        resp = client.post(
            "/onboarding",
            headers={"Authorization": "Bearer invalido"},
            json={"symbol": "ATOMUSDT", "timeframe": "15m", "leverage": 3},
        )
        assert resp.status_code == 401
        assert resp.json()["error"] == "unauthorized"

    def test_escrita_permite_bearer_valido_quando_requerida(self) -> None:
        app, _ = _make_app(auth_required=True, auth_token="token123")
        client = TestClient(app)
        resp = client.post(
            "/onboarding",
            headers={"Authorization": "Bearer token123"},
            json={"symbol": "ATOMUSDT", "timeframe": "15m", "leverage": 3},
        )
        assert resp.status_code == 201

    def test_gets_permanecem_livres_quando_auth_requerida(self) -> None:
        app, _ = _make_app(auth_required=True, auth_token="token123")
        client = TestClient(app)
        resp = client.get("/onboarding")
        assert resp.status_code == 200
