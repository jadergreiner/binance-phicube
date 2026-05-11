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
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.onboarding import _approved_triplets, _merge_triplets, router

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
    _jobs: dict[str, dict] = {}
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

    async def _create_job(doc: dict):
        _jobs[doc["job_id"]] = dict(doc)

    async def _get_job(job_id: str):
        return _jobs.get(job_id)

    async def _get_active_job(idempotency_key: str):
        for job in _jobs.values():
            if job.get("idempotency_key") == idempotency_key and job.get("status") in {
                "queued",
                "running",
            }:
                return job
        return None

    async def _update_job(job_id: str, update: dict) -> bool:
        if job_id not in _jobs:
            return False
        _jobs[job_id].update(update)
        _jobs[job_id]["updated_at"] = datetime.now(UTC)
        return True

    repo.get_onboarding_session = _get
    repo.list_onboarding_sessions = _list
    repo.create_onboarding_session = _create
    repo.update_onboarding_session = _update
    repo.delete_onboarding_session = _delete
    repo.create_backtest_job = _create_job
    repo.get_backtest_job = _get_job
    repo.get_active_backtest_job_by_key = _get_active_job
    repo.update_backtest_job = _update_job

    app.state.repository = repo

    settings = MagicMock()
    cfg_list = []
    symbols = active_symbols if active_symbols is not None else {"BTCUSDT", "ETHUSDT"}
    for sym in sorted(symbols):
        c = MagicMock()
        c.symbol = sym
        c.timeframe = "15m"
        c.leverage = 5
        cfg_list.append(c)
    settings.symbol_timeframes = cfg_list
    settings.dashboard_write_auth_required = auth_required
    settings.dashboard_write_auth_token = auth_token
    settings.onboarding_backtest_job_run_inline = True
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


def _approved_session(symbol: str = "ATOMUSDT") -> dict:
    s = _backtested_session(symbol)
    s["status"] = "APPROVED"
    s["config_string"] = f"{symbol}:15m:3"
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

    def test_criar_sessao_candidata_alfanumerica(self) -> None:
        app, store = _make_app()
        client = TestClient(app)

        resp = client.post(
            "/onboarding",
            json={"symbol": "BROCCOLI714USDT", "timeframe": "15m", "leverage": 3},
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["symbol"] == "BROCCOLI714USDT"
        assert data["status"] == "CANDIDATE"
        assert "BROCCOLI714USDT" in store


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
    """TEST_019_04 — POST /onboarding/{symbol}/backtest-jobs executa job e atualiza sessão."""

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

            resp = client.post("/onboarding/ATOMUSDT/backtest-jobs", json={"limit": 35000})

        assert resp.status_code == 202
        assert resp.json()["status"] == "succeeded"
        assert store["ATOMUSDT"]["status"] == "BACKTESTED"
        assert store["ATOMUSDT"]["backtest_result"] is not None

    def test_backtest_em_approved_mantem_status_approved(self) -> None:
        from datetime import UTC, datetime

        from src.backtest.models import BacktestResult

        app, store = _make_app(sessions=[_approved_session("ATOMUSDT")])
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

            resp = client.post("/onboarding/ATOMUSDT/backtest-jobs", json={"limit": 35000})

        assert resp.status_code == 202
        assert resp.json()["status"] == "succeeded"
        assert store["ATOMUSDT"]["status"] == "APPROVED"
        assert store["ATOMUSDT"]["backtest_result"] is not None


# ─── TEST_019_05: aprovação gera config_string ───────────────────────────────


class TestAprovacaoGeraConfig:
    """TEST_019_05 — POST /onboarding/{symbol}/approve → config_string preenchida."""

    def test_aprovar_gera_config_string(self) -> None:
        app, store = _make_app(sessions=[_backtested_session("ATOMUSDT")])
        client = TestClient(app)

        with TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            with patch("src.api.routes.onboarding._resolve_env_path", return_value=env_path):
                resp = client.post("/onboarding/ATOMUSDT/approve", json={})

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "APPROVED"
        assert data["config_string"] is not None
        assert "ATOMUSDT" in data["config_string"]
        assert data["symbol_timeframes_line"] == "BTCUSDT:15m:5,ETHUSDT:15m:5,ATOMUSDT:15m:3"
        assert data["env_applied"] is True
        assert data["sync_status"]["consistency_status"] == "CONSISTENT"
        assert "operational_checklist" in data
        assert len(data["operational_checklist"]) == 3


# ─── TEST_019_06: config_string formato correto ───────────────────────────────


class TestConfigStringFormato:
    """TEST_019_06 — config_string = SYMBOL:TIMEFRAME:LEVERAGE."""

    def test_config_string_formato(self) -> None:
        app, _ = _make_app(sessions=[_backtested_session("ATOMUSDT")])
        client = TestClient(app)

        with TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            with patch("src.api.routes.onboarding._resolve_env_path", return_value=env_path):
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

    def test_deletar_sessao_approved_reconcilia_env(self) -> None:
        app, store = _make_app(sessions=[_approved_session("ATOMUSDT")])
        client = TestClient(app)

        with TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            with patch("src.api.routes.onboarding._resolve_env_path", return_value=env_path):
                resp = client.delete("/onboarding/ATOMUSDT")

        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted_symbol"] == "ATOMUSDT"
        assert data["sync_status"]["consistency_status"] == "CONSISTENT"
        assert "ATOMUSDT" not in data["symbol_timeframes_line"]
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

        resp = client.post("/onboarding/NAOEXISTE/backtest-jobs", json={})

        assert resp.status_code == 404


class TestBacktestLegadoDesativado:
    """Endpoint legado síncrono deve retornar 410 com instrução de migração."""

    def test_backtest_legado_retorna_410_com_migration(self) -> None:
        app, _ = _make_app(sessions=[_session("ATOMUSDT")])
        client = TestClient(app)

        resp = client.post("/onboarding/ATOMUSDT/backtest", json={"limit": 35000})

        assert resp.status_code == 410
        payload = resp.json()
        assert payload["error_code"] == "legacy_endpoint_deprecated"
        assert "/onboarding/ATOMUSDT/backtest-jobs" == payload["migration"]["create_job"]
        assert "/onboarding/backtest-jobs/{job_id}" == payload["migration"]["get_job"]


class TestBacktestJobs:
    def test_consulta_job_por_id(self) -> None:
        from src.backtest.models import BacktestResult

        app, _ = _make_app(sessions=[_session("ATOMUSDT")])
        client = TestClient(app)

        mock_result = BacktestResult(
            symbol="ATOMUSDT",
            timeframe="15m",
            candles_used=1000,
            total_trades=10,
            win_rate_pct=50.0,
            profit_factor=1.2,
            max_drawdown_usdt=-10.0,
            total_pnl_usdt=12.0,
            avg_rrr=1.0,
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
            create_resp = client.post("/onboarding/ATOMUSDT/backtest-jobs", json={"limit": 35000})

        assert create_resp.status_code == 202
        job_id = create_resp.json()["job_id"]
        get_resp = client.get(f"/onboarding/backtest-jobs/{job_id}")
        assert get_resp.status_code == 200
        payload = get_resp.json()
        assert payload["status"] == "succeeded"
        assert payload["backtest_result"]["symbol"] == "ATOMUSDT"

    def test_timeout_do_executor_marca_job_como_failed(self) -> None:
        app, _ = _make_app(sessions=[_session("ATOMUSDT")])
        client = TestClient(app)

        async def _raise_timeout(_):
            raise TimeoutError

        with patch(
            "src.api.routes.onboarding._BacktestJobExecutor.run",
            side_effect=_raise_timeout,
        ):
            create_resp = client.post("/onboarding/ATOMUSDT/backtest-jobs", json={"limit": 35000})

        assert create_resp.status_code == 202
        payload = create_resp.json()
        assert payload["status"] == "failed"
        assert payload["error_code"] == "timeout"


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


class TestPatchSessaoOnboarding:
    """SPEC_024 — edição de sessão de onboarding."""

    def test_patch_approved_atualiza_config_env_e_mantem_status(self) -> None:
        app, store = _make_app(sessions=[_approved_session("ATOMUSDT")])
        client = TestClient(app)

        with TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            with patch("src.api.routes.onboarding._resolve_env_path", return_value=env_path):
                resp = client.patch(
                    "/onboarding/ATOMUSDT",
                    json={"symbol": "SOLUSDT", "timeframe": "1h", "leverage": 7},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "SOLUSDT"
        assert data["status"] == "APPROVED"
        assert data["config_string"] == "SOLUSDT:1h:7"
        assert data["env_applied"] is True
        assert data["sync_status"]["consistency_status"] == "CONSISTENT"
        assert "SOLUSDT:1h:7" in data["symbol_timeframes_line"]
        assert "ATOMUSDT" not in store
        assert "SOLUSDT" in store

    def test_patch_rename_para_simbolo_ativo_retorna_409(self) -> None:
        app, _ = _make_app(sessions=[_approved_session("ATOMUSDT")], active_symbols={"SOLUSDT"})
        client = TestClient(app)

        resp = client.patch("/onboarding/ATOMUSDT", json={"symbol": "SOLUSDT"})

        assert resp.status_code == 409
        assert resp.json()["error"] == "simbolo_ja_ativo"

    def test_patch_rename_para_sessao_existente_retorna_409(self) -> None:
        app, _ = _make_app(sessions=[_approved_session("ATOMUSDT"), _session("SOLUSDT")])
        client = TestClient(app)

        resp = client.patch("/onboarding/ATOMUSDT", json={"symbol": "SOLUSDT"})

        assert resp.status_code == 409
        assert resp.json()["error"] == "sessao_ja_existe"

    def test_patch_payload_invalido_retorna_422(self) -> None:
        app, _ = _make_app(sessions=[_approved_session("ATOMUSDT")])
        client = TestClient(app)

        resp = client.patch("/onboarding/ATOMUSDT", json={"leverage": 99})

        assert resp.status_code == 422
        assert resp.json()["error"] == "leverage_invalido"


class TestMarketAnalysisOnboarding:
    """SPEC_024 — análise técnica sob demanda por símbolo."""

    def test_market_analysis_sucesso_sem_sinal(self) -> None:
        app, _ = _make_app(sessions=[_approved_session("ATOMUSDT")])
        client = TestClient(app)

        frame = pd.DataFrame(
            {
                "open_time": pd.date_range("2026-01-01", periods=80, freq="15min", tz="UTC"),
                "open": [10 + i * 0.01 for i in range(80)],
                "high": [10.2 + i * 0.01 for i in range(80)],
                "low": [9.8 + i * 0.01 for i in range(80)],
                "close": [10.1 + i * 0.01 for i in range(80)],
                "volume": [1000 + i for i in range(80)],
            }
        )

        with (
            patch("src.api.routes.onboarding.SignalEngine.evaluate", return_value=None),
            patch("src.exchange.binance_client.BinanceClient") as MockClient,
            patch("src.config.settings.get_settings") as mock_settings,
        ):
            mock_settings.return_value = MagicMock(risk_reward_ratio=2.0)
            mock_client_inst = AsyncMock()
            mock_client_inst.fetch_ohlcv_with_retry = AsyncMock(return_value=frame)
            MockClient.return_value = mock_client_inst

            resp = client.post("/onboarding/ATOMUSDT/market-analysis")

        assert resp.status_code == 200
        data = resp.json()
        assert data["signal_detected"] is False
        assert data["signal"] is None
        assert data["symbol"] == "ATOMUSDT"
        assert data["timeframe"] == "15m"
        assert "context" in data
        assert "ao" in data["context"]

    def test_market_analysis_falha_binance_retorna_503(self) -> None:
        app, _ = _make_app(sessions=[_approved_session("ATOMUSDT")])
        client = TestClient(app)

        with (
            patch("src.exchange.binance_client.BinanceClient") as MockClient,
            patch("src.config.settings.get_settings"),
        ):
            mock_client_inst = AsyncMock()
            mock_client_inst.fetch_ohlcv_with_retry = AsyncMock(side_effect=RuntimeError("boom"))
            MockClient.return_value = mock_client_inst

            resp = client.post("/onboarding/ATOMUSDT/market-analysis")

        assert resp.status_code == 503
        assert resp.json()["error"] == "market_analysis_unavailable"


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


class TestConsistenciaOnboarding:
    def test_consistency_endpoint_retorna_consistent(self) -> None:
        app, _ = _make_app(sessions=[_approved_session("ATOMUSDT")])
        client = TestClient(app)

        with TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text(
                "SYMBOL_TIMEFRAMES=BTCUSDT:15m:5,ETHUSDT:15m:5,ATOMUSDT:15m:3\n",
                encoding="utf-8",
            )
            with patch("src.api.routes.onboarding._resolve_env_path", return_value=env_path):
                resp = client.get("/onboarding/consistency")

        assert resp.status_code == 200
        data = resp.json()
        assert data["consistency_status"] == "CONSISTENT"
        assert data["divergence_reason"] is None

    def test_consistency_endpoint_retorna_degraded(self) -> None:
        app, _ = _make_app(sessions=[_approved_session("ATOMUSDT")])
        client = TestClient(app)

        with TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text("SYMBOL_TIMEFRAMES=BTCUSDT:15m:5,ETHUSDT:15m:5\n", encoding="utf-8")
            with patch("src.api.routes.onboarding._resolve_env_path", return_value=env_path):
                resp = client.get("/onboarding/consistency")

        assert resp.status_code == 200
        data = resp.json()
        assert data["consistency_status"] == "DEGRADED"
        assert data["divergence_reason"] == "env_symbol_timeframes_mismatch"

    def test_approve_com_falha_no_env_retorna_degraded(self) -> None:
        app, _ = _make_app(sessions=[_backtested_session("ATOMUSDT")])
        client = TestClient(app)

        with (
            patch("src.api.routes.onboarding._resolve_env_path", return_value=Path("C:/tmp/.env")),
            patch("src.api.routes.onboarding._upsert_env_key", side_effect=PermissionError),
        ):
            resp = client.post("/onboarding/ATOMUSDT/approve", json={})

        assert resp.status_code == 200
        data = resp.json()
        assert data["sync_status"]["consistency_status"] == "DEGRADED"
        assert data["env_applied"] is False
        assert data["env_apply_error"] == "PermissionError"


class TestReconciliacaoTriplets:
    def test_merge_triplets_deduplica_por_symbol_timeframe(self) -> None:
        merged = _merge_triplets(
            ["BTCUSDT:15m:5", "ETHUSDT:15m:5"],
            ["ETHUSDT:15m:10", "ATOMUSDT:15m:3"],
        )
        assert merged == ["BTCUSDT:15m:5", "ETHUSDT:15m:10", "ATOMUSDT:15m:3"]

    def test_approved_triplets_ignora_config_string_invalido(self) -> None:
        sessions = [
            {"status": "APPROVED", "config_string": "ATOMUSDT:15m:3"},
            {"status": "APPROVED", "config_string": "invalido"},
            {"status": "CANDIDATE", "config_string": "SOLUSDT:1h:7"},
        ]
        approved = _approved_triplets(sessions)
        assert approved == ["ATOMUSDT:15m:3"]
