"""Testes da API de autenticação do dashboard."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.api import main as api_main
from src.api.auth.strategies.auth_strategy import AuthResult
from src.config.settings import Settings


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


def test_login_redireciona_e_callback_redireciona_para_frontend(monkeypatch) -> None:
    """GET /auth/login deve emitir state e o callback deve redirecionar para a SPA."""
    _patch_lifespan(monkeypatch)

    class _FakeAuthenticator:
        def __init__(self) -> None:
            self.calls = 0

        async def authenticate(self, request):
            self.calls += 1
            if self.calls == 1:
                return AuthResult(
                    success=False,
                    error="redirect",
                    user="https://accounts.google.com/o/oauth2/v2/auth?state=state-123",
                    state="state-123",
                )

            return AuthResult(
                success=True,
                token="jwt-token",
                user="user@example.com",
                auth_method="google",
            )

    fake_authenticator = _FakeAuthenticator()
    monkeypatch.setattr("src.api.routes.auth.get_authenticator", lambda: fake_authenticator)
    monkeypatch.setattr(
        "src.api.routes.auth.get_settings",
        lambda: SimpleNamespace(
            auth_dev_bypass=False,
            google_redirect_uri=None,
            auth_post_login_redirect_uri="http://localhost:3000/auth/callback",
        ),
    )

    with TestClient(api_main.create_app()) as client:
        login_response = client.get("/auth/login", follow_redirects=False)

        assert login_response.status_code in (302, 307)
        assert login_response.headers["location"] == (
            "https://accounts.google.com/o/oauth2/v2/auth?state=state-123"
        )
        assert client.cookies.get("phicube_oauth_state") == "state-123"
        assert client.cookies.get("phicube_post_login_redirect").strip('"') == "/"

        callback_response = client.get(
            "/auth/callback",
            params={"code": "code-123", "state": "state-123"},
            follow_redirects=False,
        )

    assert callback_response.status_code in (302, 307)
    assert callback_response.headers["location"] == (
        "http://localhost:3000/auth/callback?access_token=jwt-token&redirect=%2F"
    )
    assert fake_authenticator.calls == 2


def test_callback_rejeita_state_invalido(monkeypatch) -> None:
    """Callback OAuth deve rejeitar state ausente ou divergente."""
    _patch_lifespan(monkeypatch)

    class _FakeAuthenticator:
        def __init__(self) -> None:
            self.calls = 0

        async def authenticate(self, request):
            self.calls += 1
            return AuthResult(
                success=True,
                token="jwt-token",
                user="user@example.com",
                auth_method="google",
            )

    fake_authenticator = _FakeAuthenticator()
    monkeypatch.setattr("src.api.routes.auth.get_authenticator", lambda: fake_authenticator)
    monkeypatch.setattr(
        "src.api.routes.auth.get_settings",
        lambda: SimpleNamespace(
            auth_dev_bypass=False,
            google_redirect_uri=None,
            auth_post_login_redirect_uri="http://localhost:3000/auth/callback",
        ),
    )

    with TestClient(api_main.create_app()) as client:
        client.cookies.set("phicube_oauth_state", "state-123")

        response = client.get(
            "/auth/callback",
            params={"code": "code-123", "state": "state-diferente"},
            follow_redirects=False,
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "State inválido"}
    assert fake_authenticator.calls == 0


def test_settings_genera_jwt_secret_automaticamente() -> None:
    """JWT secret deve ser gerado quando o ambiente não fornece um valor."""
    settings = Settings(binance_api_key="k", binance_api_secret="s")

    assert settings.jwt_secret is not None
    assert len(settings.jwt_secret) > 10
