"""Testes unitários da API do dashboard de consulta de posições."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.api import main as api_main


class _FakeStream:
    def __init__(
        self, *, positions: list[object], status: str, account_equity_usdt: float | None = None
    ) -> None:
        self._positions = positions
        self._status = status
        self._account_equity_usdt = account_equity_usdt

    def get_positions(self) -> list[object]:
        return list(self._positions)

    def get_status(self) -> str:
        return self._status

    def get_account_equity_usdt(self) -> float | None:
        return self._account_equity_usdt


def _make_position(*, symbol: str, updated_at: datetime) -> SimpleNamespace:
    return SimpleNamespace(
        symbol=symbol,
        side="LONG",
        quantity=0.5,
        leverage=10,
        entry_price=95000.0,
        mark_price=96000.0,
        unrealized_pnl_usdt=250.0,
        margin_used_usdt=2400.0,
        liquidation_price=87000.0,
        updated_at=updated_at,
    )


def _patch_lifespan(monkeypatch) -> None:
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
    monkeypatch.setattr(api_main.PositionStream, "start", AsyncMock(return_value=True))
    monkeypatch.setattr(api_main.PositionStream, "get_status", lambda self: "online")
    monkeypatch.setattr(api_main.PositionStream, "stop", AsyncMock(return_value=None))
    monkeypatch.setattr(api_main.AdaptiveUpdater, "start", AsyncMock(return_value=None))
    monkeypatch.setattr(api_main.AdaptiveUpdater, "stop", AsyncMock(return_value=None))


def test_lifespan_inicializa_e_encerra_recursos_na_ordem_correta(monkeypatch) -> None:
    """O lifespan deve inicializar e encerrar os recursos do dashboard na ordem esperada."""
    eventos: list[str] = []
    app = api_main.create_app()

    async def _connect(self) -> None:
        eventos.append("connect")

    async def _close(self) -> None:
        eventos.append("close")

    async def _stream_start(self) -> None:
        eventos.append("stream.start")
        self._status = "online"  # type: ignore[attr-defined]

    async def _stream_stop(self) -> None:
        eventos.append("stream.stop")

    async def _updater_start(self, stream) -> None:
        eventos.append("updater.start")
        assert stream is app.state.position_stream

    async def _updater_stop(self) -> None:
        eventos.append("updater.stop")

    monkeypatch.setattr(
        api_main,
        "get_settings",
        lambda: SimpleNamespace(
            dashboard_api_key="dash_key",
            dashboard_api_secret="dash_secret",
            binance_testnet=True,
        ),
    )
    monkeypatch.setattr(api_main.DashboardClient, "connect", _connect)
    monkeypatch.setattr(api_main.DashboardClient, "close", _close)
    monkeypatch.setattr(api_main.PositionStream, "start", _stream_start)
    monkeypatch.setattr(api_main.PositionStream, "get_status", lambda self: "online")
    monkeypatch.setattr(api_main.PositionStream, "stop", _stream_stop)
    monkeypatch.setattr(api_main.AdaptiveUpdater, "start", _updater_start)
    monkeypatch.setattr(api_main.AdaptiveUpdater, "stop", _updater_stop)

    with TestClient(app) as client:
        assert client.app.state.stream is client.app.state.position_stream
        assert client.app.state.dashboard_client is not None

    assert eventos == [
        "connect",
        "stream.start",
        "updater.start",
        "updater.stop",
        "stream.stop",
        "close",
    ]


def test_get_positions_retorna_snapshot_json_valido(monkeypatch) -> None:
    """GET /positions deve devolver posições e resumo agregados."""
    _patch_lifespan(monkeypatch)

    with TestClient(api_main.create_app()) as client:
        client.app.state.position_stream = _FakeStream(
            positions=[
                _make_position(
                    symbol="BTCUSDT",
                    updated_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
                )
            ],
            status="online",
        )

        response = client.get("/positions")

    assert response.status_code == 200
    expected = {
        "positions": [
            {
                "symbol": "BTCUSDT",
                "side": "LONG",
                "quantity": 0.5,
                "leverage": 10,
                "entry_price": 95000.0,
                "sl_price": None,
                "tp_price": None,
                "mark_price": 96000.0,
                "unrealized_pnl_usdt": 250.0,
                "margin_used_usdt": 2400.0,
                "position_size_usdt": 24000.0,
                "roi_adjusted_pct": 1.0416666666666667,
                "liquidation_price": 87000.0,
                "updated_at": "2026-05-01T12:30:00Z",
                "updated_at_br": "01/05/2026 09:30:00",
            }
        ],
        "summary": {
            "total_exposure_usdt": 24000.0,
            "total_margin_used_usdt": 2400.0,
            "total_unrealized_pnl_usdt": 250.0,
            "account_equity_usdt": None,
            "exposure_to_equity_ratio": None,
            "connection_status": "online",
            "last_update_at": "2026-05-01T12:30:00Z",
            "last_update_at_br": "01/05/2026 09:30:00",
        },
        "status": "online",
        "signal_telemetry": [],
        "timezone": "America/Sao_Paulo",
        "analysis": {
            "bias": {
                "direction": "LONG",
                "confidence": "high",
                "score": 1.0,
                "reason": (
                    "Bias LONG: exposicao LONG de 24000.00 contra 0.00 do lado oposto. "
                    "Forca do bias: 100%."
                ),
            },
            "opportunities": [
                {
                    "symbol": "BTCUSDT",
                    "direction": "LONG",
                    "action": "ADD",
                    "rationale": (
                        "O mercado favorece LONG e esta posicao possui a maior "
                        "exposicao LONG atual. Considere reforcar a tendencia ou manter a posicao."
                    ),
                    "exposure_usdt": 24000.0,
                }
            ],
            "bias_views": {
                "active": "allocation",
                "views": [
                    {
                        "id": "allocation",
                        "direction": "LONG",
                        "confidence": "high",
                        "score": 1.0,
                        "reason": (
                            "Bias LONG: exposicao LONG de 24000.00 contra 0.00 do lado oposto. "
                            "Forca do bias: 100%."
                        ),
                        "metrics": {
                            "long_exposure": 24000.0,
                            "short_exposure": 0.0,
                            "relative_balance": 1.0,
                            "net_exposure": 24000.0,
                            "total_exposure": 24000.0,
                        },
                    },
                    {
                        "id": "pnl_weighted",
                        "direction": "NEUTRAL",
                        "confidence": "low",
                        "score": 0.010416666666666666,
                        "reason": (
                            "PnL ajustado por exposicao sem dominancia clara entre LONG e SHORT."
                        ),
                        "metrics": {
                            "long_pnl": 250.0,
                            "short_pnl": 0.0,
                            "long_pnl_ratio": 0.010416666666666666,
                            "short_pnl_ratio": 0.0,
                            "net_pnl_ratio": 0.010416666666666666,
                        },
                    },
                    {
                        "id": "concentration",
                        "direction": "LONG",
                        "confidence": "high",
                        "score": 1.0,
                        "reason": "Concentracao em BTCUSDT: 100% da exposicao total no lado LONG.",
                        "metrics": {
                            "top_symbol": "BTCUSDT",
                            "top_share": 1.0,
                            "top_exposure": 24000.0,
                            "total_exposure": 24000.0,
                        },
                    },
                ],
                "divergence": {
                    "has_divergence": True,
                    "summary": "allocation=LONG ; pnl_weighted=NEUTRAL ; concentration=LONG",
                },
            },
        },
    }
    assert response.json() == expected, response.json()


def test_get_health_retorna_status_degradado(monkeypatch) -> None:
    """GET /health deve refletir o status real do stream."""
    _patch_lifespan(monkeypatch)

    with TestClient(api_main.create_app()) as client:
        client.app.state.position_stream = _FakeStream(positions=[], status="degraded")

        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "degraded"}


def test_get_positions_retornara_503_quando_stream_inativo(monkeypatch) -> None:
    """GET /positions deve retornar 503 quando o stream estiver offline."""
    _patch_lifespan(monkeypatch)

    with TestClient(api_main.create_app()) as client:
        client.app.state.position_stream = _FakeStream(positions=[], status="offline")

        response = client.get("/positions")

    assert response.status_code == 503
    assert response.json() == {"status": "offline"}


def test_get_root_entrega_pagina_frontend_index_html(monkeypatch) -> None:
    """GET / deve entregar a página principal do frontend."""
    _patch_lifespan(monkeypatch)

    with TestClient(api_main.create_app()) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Consulta de Posições" in response.text
    assert "<html" in response.text.lower()


def test_get_positions_retorna_snapshot_com_fallback_de_calculo(monkeypatch) -> None:
    """GET /positions deve aceitar position_size_usdt indefinido e aplicar fallback."""
    _patch_lifespan(monkeypatch)

    valid_position = _make_position(
        symbol="BTCUSDT",
        updated_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
    )
    valid_position.position_size_usdt = None

    invalid_position = _make_position(
        symbol="ETHUSDT",
        updated_at=datetime(2026, 5, 1, 12, 31, tzinfo=UTC),
    )
    invalid_position.leverage = 0
    invalid_position.position_size_usdt = None

    with TestClient(api_main.create_app()) as client:
        client.app.state.position_stream = _FakeStream(
            positions=[valid_position, invalid_position],
            status="online",
        )

        response = client.get("/positions")

    assert response.status_code == 200
    payload = response.json()

    assert payload["summary"]["total_exposure_usdt"] == pytest.approx(24000.0)
    assert payload["summary"]["total_margin_used_usdt"] == pytest.approx(4800.0)
    assert payload["summary"]["total_unrealized_pnl_usdt"] == pytest.approx(500.0)
    assert payload["positions"][0]["position_size_usdt"] == pytest.approx(24000.0)
    assert payload["positions"][1]["position_size_usdt"] is None
    assert payload["positions"][1]["roi_adjusted_pct"] is None
    assert payload["analysis"]["bias"]["direction"] == "LONG"
    assert payload["analysis"]["opportunities"][0]["symbol"] == "BTCUSDT"
    assert payload["signal_telemetry"] == []


def test_get_positions_calcula_exposure_to_equity_ratio_quando_equity_disponivel(
    monkeypatch
) -> None:
    """GET /positions calcula exposure_to_equity_ratio quando há equity no stream."""
    _patch_lifespan(monkeypatch)

    with TestClient(api_main.create_app()) as client:
        client.app.state.position_stream = _FakeStream(
            positions=[
                _make_position(
                    symbol="BTCUSDT",
                    updated_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
                )
            ],
            status="online",
            account_equity_usdt=12000.0,
        )

        response = client.get("/positions")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["account_equity_usdt"] == pytest.approx(12000.0)
    assert payload["summary"]["exposure_to_equity_ratio"] == pytest.approx(2.0)


def test_websocket_positions_emite_snapshot_inicial(monkeypatch) -> None:
    """WS /ws/positions deve enviar snapshot inicial ao conectar."""
    _patch_lifespan(monkeypatch)

    with TestClient(api_main.create_app()) as client:
        client.app.state.position_stream = _FakeStream(
            positions=[
                _make_position(
                    symbol="BTCUSDT",
                    updated_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
                )
            ],
            status="online",
        )

        with client.websocket_connect("/ws/positions") as websocket:
            payload = websocket.receive_json()

    assert payload["status"] == "online"
    assert payload["timezone"] == "America/Sao_Paulo"
    assert "signal_telemetry" in payload
    assert payload["positions"][0]["symbol"] == "BTCUSDT"
    assert payload["analysis"]["bias"]["direction"] == "LONG"
    assert payload["analysis"]["bias_views"]["active"] == "allocation"
    assert payload["analysis"]["opportunities"][0]["action"] == "ADD"


def test_websocket_positions_inclui_analysis_no_snapshot_inicial(monkeypatch) -> None:
    """WS /ws/positions deve incluir objeto analysis no snapshot inicial."""
    _patch_lifespan(monkeypatch)

    with TestClient(api_main.create_app()) as client:
        client.app.state.position_stream = _FakeStream(
            positions=[
                _make_position(
                    symbol="BTCUSDT",
                    updated_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
                )
            ],
            status="online",
        )

        with client.websocket_connect("/ws/positions") as websocket:
            payload = websocket.receive_json()

    assert payload["analysis"]["bias"]["direction"] == "LONG"
    assert payload["timezone"] == "America/Sao_Paulo"
    assert "signal_telemetry" in payload
    assert payload["analysis"]["bias"]["confidence"] == "high"
    assert payload["analysis"]["bias_views"]["divergence"]["has_divergence"] is True
    assert payload["analysis"]["opportunities"][0]["action"] == "ADD"


def test_get_positions_expoe_signal_telemetry_quando_repositorio_disponivel(monkeypatch) -> None:
    """Snapshot deve incluir diagnóstico de última avaliação por símbolo."""
    _patch_lifespan(monkeypatch)

    repo = AsyncMock()
    repo.get_open_trade_sl_tp = AsyncMock(return_value={})
    repo.get_latest_signal_diagnostics = AsyncMock(
        return_value=[
            {
                "symbol": "BTCUSDT",
                "timeframe": "15m",
                "decision": "NO_SIGNAL",
                "signal_generated": False,
                "reason": "long_missing:close_above_fractal;short_missing:ao_negative",
                "evaluated_at": datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
            }
        ]
    )

    with TestClient(api_main.create_app()) as client:
        client.app.state.repository = repo
        client.app.state.position_stream = _FakeStream(
            positions=[
                _make_position(
                    symbol="BTCUSDT",
                    updated_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
                )
            ],
            status="online",
        )
        response = client.get("/positions")

    assert response.status_code == 200
    telemetry = response.json()["signal_telemetry"]
    assert len(telemetry) == 1
    assert telemetry[0]["symbol"] == "BTCUSDT"
    assert telemetry[0]["decision"] == "NO_SIGNAL"
    assert telemetry[0]["evaluated_at"] == "2026-05-01T12:30:00Z"
    assert telemetry[0]["evaluated_at_br"] == "01/05/2026 09:30:00"


def test_lifespan_mantem_aplicacao_no_ar_quando_binance_falha(monkeypatch) -> None:
    """O startup não deve derrubar a API se a conexão com a Binance falhar."""
    monkeypatch.setattr(
        api_main,
        "get_settings",
        lambda: SimpleNamespace(
            dashboard_api_key="dash_key",
            dashboard_api_secret="dash_secret",
            binance_testnet=True,
        ),
    )
    monkeypatch.setattr(
        api_main.DashboardClient,
        "connect",
        AsyncMock(side_effect=RuntimeError("timestamp skew")),
    )
    monkeypatch.setattr(api_main.DashboardClient, "close", AsyncMock(return_value=None))
    monkeypatch.setattr(api_main.PositionStream, "start", AsyncMock(return_value=True))
    monkeypatch.setattr(api_main.PositionStream, "get_status", lambda self: "online")
    monkeypatch.setattr(api_main.PositionStream, "stop", AsyncMock(return_value=None))
    monkeypatch.setattr(api_main.AdaptiveUpdater, "start", AsyncMock(return_value=None))
    monkeypatch.setattr(api_main.AdaptiveUpdater, "stop", AsyncMock(return_value=None))

    with TestClient(api_main.create_app()) as client:
        assert client.app.state.startup_mode == "online"
        response = client.get("/")

    assert response.status_code == 200
    assert "Consulta de Posições" in response.text
