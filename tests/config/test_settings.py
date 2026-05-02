from __future__ import annotations

from typing import Any, cast
from unittest.mock import patch

from src.config.settings import Settings


def _build_settings() -> Settings:
    with patch.dict(Settings.model_config, {"env_file": None}):
        return cast(Any, Settings)()


def test_prefere_dashboard_testnet_quando_binance_testnet_ativo(
    monkeypatch,
) -> None:
    monkeypatch.setenv("BINANCE_API_KEY", "bot_key")
    monkeypatch.setenv("BINANCE_API_SECRET", "bot_secret")
    monkeypatch.setenv("BINANCE_TESTNET", "true")
    monkeypatch.setenv("DASHBOARD_API_KEY", "dash_prod_key")
    monkeypatch.setenv("DASHBOARD_API_SECRET", "dash_prod_secret")
    monkeypatch.setenv("DASHBOARD_TESTNET_API_KEY", "dash_test_key")
    monkeypatch.setenv("DASHBOARD_TESTNET_API_SECRET", "dash_test_secret")

    settings = _build_settings()

    assert settings.dashboard_api_key == "dash_test_key"
    assert settings.dashboard_api_secret == "dash_test_secret"


def test_mantem_dashboard_padrao_quando_binance_testnet_desativado(
    monkeypatch,
) -> None:
    monkeypatch.setenv("BINANCE_API_KEY", "bot_key")
    monkeypatch.setenv("BINANCE_API_SECRET", "bot_secret")
    monkeypatch.setenv("BINANCE_TESTNET", "false")
    monkeypatch.setenv("DASHBOARD_API_KEY", "dash_prod_key")
    monkeypatch.setenv("DASHBOARD_API_SECRET", "dash_prod_secret")
    monkeypatch.setenv("DASHBOARD_TESTNET_API_KEY", "dash_test_key")
    monkeypatch.setenv("DASHBOARD_TESTNET_API_SECRET", "dash_test_secret")

    settings = _build_settings()

    assert settings.dashboard_api_key == "dash_prod_key"
    assert settings.dashboard_api_secret == "dash_prod_secret"


def test_faz_fallback_para_dashboard_padrao_sem_credenciais_testnet(
    monkeypatch,
) -> None:
    monkeypatch.setenv("BINANCE_API_KEY", "bot_key")
    monkeypatch.setenv("BINANCE_API_SECRET", "bot_secret")
    monkeypatch.setenv("BINANCE_TESTNET", "true")
    monkeypatch.setenv("DASHBOARD_API_KEY", "dash_prod_key")
    monkeypatch.setenv("DASHBOARD_API_SECRET", "dash_prod_secret")
    monkeypatch.delenv("DASHBOARD_TESTNET_API_KEY", raising=False)
    monkeypatch.delenv("DASHBOARD_TESTNET_API_SECRET", raising=False)

    settings = _build_settings()

    assert settings.dashboard_api_key == "dash_prod_key"
    assert settings.dashboard_api_secret == "dash_prod_secret"
