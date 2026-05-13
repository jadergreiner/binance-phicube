"""Testes do endpoint GET /health com suporte a Circuit Breakers (SPEC_034)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.health import router
from src.resilience import CircuitBreakerRegistry, CircuitBreakerState


def _make_app(
    repo=None,
    resilient_client=None,
    resilient_repo=None,
) -> FastAPI:
    """Cria app de teste com repositório e clientes resilientes injetados."""
    app = FastAPI()
    app.include_router(router)
    if repo is not None:
        app.state.repository = repo
    if resilient_client is not None:
        app.state.resilient_client = resilient_client
    if resilient_repo is not None:
        app.state.resilient_repo = resilient_repo
    return app


def _make_repo(ping_ok: bool = True, heartbeat_result=None) -> AsyncMock:
    """Cria mock de repositório com ping e heartbeat."""
    mock_repo = AsyncMock()
    mock_repo.database = AsyncMock()
    if ping_ok:
        mock_repo.database.command = AsyncMock(return_value={"ok": 1})
    else:
        mock_repo.database.command = AsyncMock(side_effect=Exception("connection refused"))
    mock_repo.get_last_heartbeat_at = AsyncMock(return_value=heartbeat_result)
    return mock_repo


def _make_binance_client_healthy() -> MagicMock:
    """Cria cliente Binance resiliente com todos circuit breakers CLOSED."""
    registry = CircuitBreakerRegistry(namespace="binance")

    # Cria breakers com estado CLOSED (precisa manter referências para state_summary())
    breaker_ohlcv = registry.get("binance_fetch_ohlcv")
    breaker_ohlcv.state = CircuitBreakerState.CLOSED

    breaker_order = registry.get("binance_create_order")
    breaker_order.state = CircuitBreakerState.CLOSED

    breaker_positions = registry.get("binance_fetch_positions")
    breaker_positions.state = CircuitBreakerState.CLOSED

    client = MagicMock()
    client.registry = registry
    return client


def _make_binance_client_degraded() -> MagicMock:
    """Cria cliente Binance resiliente com fetch_ohlcv OPEN (Tipo C)."""
    registry = CircuitBreakerRegistry(namespace="binance")

    # fetch_ohlcv é Tipo C (graceful degrade)
    breaker_ohlcv = registry.get("binance_fetch_ohlcv")
    breaker_ohlcv.state = CircuitBreakerState.OPEN

    breaker_order = registry.get("binance_create_order")
    breaker_order.state = CircuitBreakerState.CLOSED

    breaker_positions = registry.get("binance_fetch_positions")
    breaker_positions.state = CircuitBreakerState.CLOSED

    client = MagicMock()
    client.registry = registry
    return client


def _make_binance_client_critical() -> MagicMock:
    """Cria cliente Binance resiliente com create_order OPEN (Tipo A)."""
    registry = CircuitBreakerRegistry(namespace="binance")

    # create_order é Tipo A (crítico)
    breaker_ohlcv = registry.get("binance_fetch_ohlcv")
    breaker_ohlcv.state = CircuitBreakerState.CLOSED

    breaker_order = registry.get("binance_create_order")
    breaker_order.state = CircuitBreakerState.OPEN

    breaker_positions = registry.get("binance_fetch_positions")
    breaker_positions.state = CircuitBreakerState.CLOSED

    client = MagicMock()
    client.registry = registry
    return client


def _make_mongodb_repo_healthy() -> MagicMock:
    """Cria repositório MongoDB resiliente com todos circuit breakers CLOSED."""
    registry = CircuitBreakerRegistry(namespace="mongodb")

    # Cria breakers com estado CLOSED
    cb_trade = registry.get("mongodb:save_trade")
    cb_trade.state = CircuitBreakerState.CLOSED

    cb_signal = registry.get("mongodb:save_signal")
    cb_signal.state = CircuitBreakerState.CLOSED

    cb_audit = registry.get("mongodb:audit_log")
    cb_audit.state = CircuitBreakerState.CLOSED

    repo = MagicMock()
    repo.registry = registry
    return repo


def _make_mongodb_repo_degraded() -> MagicMock:
    """Cria repositório MongoDB resiliente com save_signal OPEN (Tipo C)."""
    registry = CircuitBreakerRegistry(namespace="mongodb")

    # save_signal é Tipo C (graceful degrade)
    cb_trade = registry.get("mongodb:save_trade")
    cb_trade.state = CircuitBreakerState.CLOSED

    cb_signal = registry.get("mongodb:save_signal")
    cb_signal.state = CircuitBreakerState.OPEN

    cb_audit = registry.get("mongodb:audit_log")
    cb_audit.state = CircuitBreakerState.CLOSED

    repo = MagicMock()
    repo.registry = registry
    return repo


def _make_mongodb_repo_critical() -> MagicMock:
    """Cria repositório MongoDB resiliente com save_trade OPEN (Tipo B, crítico)."""
    registry = CircuitBreakerRegistry(namespace="mongodb")

    # save_trade é Tipo B (retry, crítico se abrir)
    cb_save_trade = registry.get("mongodb:save_trade")
    cb_save_trade.state = CircuitBreakerState.OPEN

    cb_save_signal = registry.get("mongodb:save_signal")
    cb_save_signal.state = CircuitBreakerState.CLOSED

    cb_audit = registry.get("mongodb:audit_log")
    cb_audit.state = CircuitBreakerState.CLOSED

    repo = MagicMock()
    repo.registry = registry
    return repo


class TestHealthCircuitBreakers:
    """Testes do suporte a circuit breakers no /health (SPEC_034)."""

    def test_health_200_com_todos_circuit_breakers_healthy(self) -> None:
        """Status 200 quando MongoDB OK e todos circuit breakers CLOSED."""
        mock_repo = _make_repo(ping_ok=True, heartbeat_result=None)
        binance_client = _make_binance_client_healthy()
        mongodb_repo = _make_mongodb_repo_healthy()

        app = _make_app(
            repo=mock_repo,
            resilient_client=binance_client,
            resilient_repo=mongodb_repo,
        )

        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["circuit_breaker_status"] == "healthy"
        assert "circuit_breakers" in data
        assert "binance" in data["circuit_breakers"]
        assert "mongodb" in data["circuit_breakers"]
        # Verifica que todos os breakers estão CLOSED
        for name, state in data["circuit_breakers"]["binance"].items():
            assert state == "closed", f"{name} deve estar closed"
        for name, state in data["circuit_breakers"]["mongodb"].items():
            assert state == "closed", f"{name} deve estar closed"

    def test_health_200_status_degraded_tipo_c_aberto(self) -> None:
        """Status 200 com circuit_breaker_status='degraded' quando Tipo C (graceful) OPEN."""
        mock_repo = _make_repo(ping_ok=True, heartbeat_result=None)
        binance_client = _make_binance_client_degraded()  # fetch_ohlcv OPEN (Tipo C)
        mongodb_repo = _make_mongodb_repo_healthy()

        app = _make_app(
            repo=mock_repo,
            resilient_client=binance_client,
            resilient_repo=mongodb_repo,
        )

        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["circuit_breaker_status"] == "degraded"
        # Verifica que fetch_ohlcv está OPEN
        assert data["circuit_breakers"]["binance"]["binance_fetch_ohlcv"] == "open"

    def test_health_200_status_critical_tipo_a_aberto(self) -> None:
        """Status 200 com circuit_breaker_status='critical' quando Tipo A (crítico) OPEN."""
        mock_repo = _make_repo(ping_ok=True, heartbeat_result=None)
        binance_client = _make_binance_client_critical()  # create_order OPEN (Tipo A)
        mongodb_repo = _make_mongodb_repo_healthy()

        app = _make_app(
            repo=mock_repo,
            resilient_client=binance_client,
            resilient_repo=mongodb_repo,
        )

        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["circuit_breaker_status"] == "critical"
        # Verifica que create_order está OPEN
        assert data["circuit_breakers"]["binance"]["binance_create_order"] == "open"

    def test_health_200_status_degraded_tipo_b_aberto(self) -> None:
        """Status 200 com circuit_breaker_status='degraded' quando Tipo B (retry) OPEN.

        Tipo B (save_trade) é importante mas não crítico pois tem fallback (journal).
        """
        mock_repo = _make_repo(ping_ok=True, heartbeat_result=None)
        binance_client = _make_binance_client_healthy()
        mongodb_repo = _make_mongodb_repo_critical()  # save_trade OPEN (Tipo B)

        app = _make_app(
            repo=mock_repo,
            resilient_client=binance_client,
            resilient_repo=mongodb_repo,
        )

        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        # Tipo B (retry com journal fallback) = degraded, não critical
        assert data["circuit_breaker_status"] == "degraded"
        # Verifica que save_trade está OPEN
        assert data["circuit_breakers"]["mongodb"]["mongodb:save_trade"] == "open"

    def test_health_503_mongodb_down_mas_retorna_circuit_breaker_info(self) -> None:
        """Status 503 quando MongoDB down, mas ainda retorna circuit breaker info."""
        mock_repo = _make_repo(ping_ok=False)
        binance_client = _make_binance_client_healthy()
        mongodb_repo = _make_mongodb_repo_healthy()

        app = _make_app(
            repo=mock_repo,
            resilient_client=binance_client,
            resilient_repo=mongodb_repo,
        )

        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "error"
        assert data["mongodb"] == "error"
        # Mesmo com erro, retorna circuit breaker info
        assert "circuit_breakers" in data
        assert data["circuit_breaker_status"] == "healthy"

    def test_health_200_sem_resilient_client_retorna_vazio(self) -> None:
        """Quando resilient_client não disponível, binance dict vazio mas sem erro."""
        mock_repo = _make_repo(ping_ok=True, heartbeat_result=None)
        mongodb_repo = _make_mongodb_repo_healthy()

        app = _make_app(
            repo=mock_repo,
            resilient_client=None,  # Não injetado
            resilient_repo=mongodb_repo,
        )

        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["circuit_breaker_status"] == "healthy"
        # Verifica que mongodb está presente, binance pode estar ausente ou vazio
        assert "circuit_breakers" in data

    def test_health_200_sem_resilient_repo_retorna_vazio(self) -> None:
        """Quando resilient_repo não disponível, mongodb dict vazio mas sem erro."""
        mock_repo = _make_repo(ping_ok=True, heartbeat_result=None)
        binance_client = _make_binance_client_healthy()

        app = _make_app(
            repo=mock_repo,
            resilient_client=binance_client,
            resilient_repo=None,  # Não injetado
        )

        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["circuit_breaker_status"] == "healthy"
        # Verifica que binance está presente, mongodb pode estar ausente ou vazio
        assert "circuit_breakers" in data

    def test_health_200_ambos_degradados_tipo_b_e_c(self) -> None:
        """Quando Tipo C E Tipo B abertos, status=degraded.

        Tipo B (retry com journal) não é crítico, é apenas degraded como Tipo C.
        """
        mock_repo = _make_repo(ping_ok=True, heartbeat_result=None)
        binance_client = _make_binance_client_degraded()  # fetch_ohlcv OPEN (Tipo C)
        mongodb_repo = _make_mongodb_repo_critical()  # save_trade OPEN (Tipo B)

        app = _make_app(
            repo=mock_repo,
            resilient_client=binance_client,
            resilient_repo=mongodb_repo,
        )

        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        # Tanto Tipo B (retry) quanto Tipo C (graceful) = degraded
        assert data["circuit_breaker_status"] == "degraded"

    def test_health_endpoint_robusto_sem_excecao_registry_invalido(self) -> None:
        """Endpoint nunca levanta exceção mesmo com registry quebrado."""
        mock_repo = _make_repo(ping_ok=True, heartbeat_result=None)

        # Cria cliente com registry que levanta exceção ao acessar a property
        bad_client = MagicMock()
        # Configura a property para levantar exceção
        type(bad_client).registry = PropertyMock(side_effect=Exception("registry error"))

        app = _make_app(
            repo=mock_repo,
            resilient_client=bad_client,
            resilient_repo=None,
        )

        with TestClient(app) as client:
            response = client.get("/health")

        # Mesmo com erro, não levanta exception (retorna 200 graciously)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "circuit_breakers" in data
        # O status deve ser healthy (nenhum CB falhou de sucesso)
        assert data["circuit_breaker_status"] == "healthy"

    def test_health_json_sempre_valido(self) -> None:
        """Resposta JSON sempre válida e com campos esperados."""
        mock_repo = _make_repo(ping_ok=True, heartbeat_result=None)
        binance_client = _make_binance_client_healthy()
        mongodb_repo = _make_mongodb_repo_healthy()

        app = _make_app(
            repo=mock_repo,
            resilient_client=binance_client,
            resilient_repo=mongodb_repo,
        )

        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Campos esperados sempre presentes
        expected_fields = [
            "status",
            "mongodb",
            "bot_process",
            "circuit_breakers",
            "circuit_breaker_status",
            "timestamp",
            "timestamp_br",
            "timezone",
        ]
        for field in expected_fields:
            assert field in data, f"Campo '{field}' faltando na resposta"

        # circuit_breakers deve ser dict
        assert isinstance(data["circuit_breakers"], dict)
        # circuit_breaker_status deve ser um dos valores válidos
        assert data["circuit_breaker_status"] in ["healthy", "degraded", "critical"]
