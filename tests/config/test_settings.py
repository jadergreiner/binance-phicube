from __future__ import annotations

from typing import Any, cast
from unittest.mock import patch

import pytest

from src.config.settings import Settings, SymbolConfig


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


def test_carrega_sem_configuracao_telegram(monkeypatch) -> None:
    """Settings deve carregar sem TELEGRAM_TOKEN e TELEGRAM_CHAT_ID."""
    monkeypatch.setenv("BINANCE_API_KEY", "bot_key")
    monkeypatch.setenv("BINANCE_API_SECRET", "bot_secret")
    monkeypatch.setenv("DASHBOARD_API_KEY", "dash_key")
    monkeypatch.setenv("DASHBOARD_API_SECRET", "dash_secret")

    settings = _build_settings()

    assert settings.telegram_token is None
    assert settings.telegram_chat_id is None


def test_carrega_com_configuracao_telegram_completa(monkeypatch) -> None:
    """Settings deve carregar com TELEGRAM_TOKEN e TELEGRAM_CHAT_ID configurados."""
    monkeypatch.setenv("BINANCE_API_KEY", "bot_key")
    monkeypatch.setenv("BINANCE_API_SECRET", "bot_secret")
    monkeypatch.setenv("DASHBOARD_API_KEY", "dash_key")
    monkeypatch.setenv("DASHBOARD_API_SECRET", "dash_secret")
    monkeypatch.setenv("TELEGRAM_TOKEN", "123456789:ABCdefGHIjklMNOpqrsTUVwxyz")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "987654321")

    settings = _build_settings()

    assert settings.telegram_token == "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
    assert settings.telegram_chat_id == "987654321"


def test_carrega_com_configuracao_telegram_parcial(monkeypatch) -> None:
    """Settings deve carregar mesmo com apenas uma variável do Telegram configurada."""
    monkeypatch.setenv("BINANCE_API_KEY", "bot_key")
    monkeypatch.setenv("BINANCE_API_SECRET", "bot_secret")
    monkeypatch.setenv("DASHBOARD_API_KEY", "dash_key")
    monkeypatch.setenv("DASHBOARD_API_SECRET", "dash_secret")
    monkeypatch.setenv("TELEGRAM_TOKEN", "123456789:ABCdefGHIjklMNOpqrsTUVwxyz")
    # TELEGRAM_CHAT_ID não configurado

    settings = _build_settings()

    assert settings.telegram_token == "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
    assert settings.telegram_chat_id is None


def test_requer_token_quando_write_auth_ativo(monkeypatch) -> None:
    monkeypatch.setenv("BINANCE_API_KEY", "bot_key")
    monkeypatch.setenv("BINANCE_API_SECRET", "bot_secret")
    monkeypatch.setenv("DASHBOARD_API_KEY", "dash_key")
    monkeypatch.setenv("DASHBOARD_API_SECRET", "dash_secret")
    monkeypatch.setenv("DASHBOARD_WRITE_AUTH_REQUIRED", "true")
    monkeypatch.delenv("DASHBOARD_WRITE_AUTH_TOKEN", raising=False)

    with pytest.raises(ValueError, match="DASHBOARD_WRITE_AUTH_TOKEN obrigatorio"):
        _build_settings()


def test_aceita_write_auth_ativo_com_token(monkeypatch) -> None:
    monkeypatch.setenv("BINANCE_API_KEY", "bot_key")
    monkeypatch.setenv("BINANCE_API_SECRET", "bot_secret")
    monkeypatch.setenv("DASHBOARD_API_KEY", "dash_key")
    monkeypatch.setenv("DASHBOARD_API_SECRET", "dash_secret")
    monkeypatch.setenv("DASHBOARD_WRITE_AUTH_REQUIRED", "true")
    monkeypatch.setenv("DASHBOARD_WRITE_AUTH_TOKEN", "token123")

    settings = _build_settings()

    assert settings.dashboard_write_auth_required is True
    assert settings.dashboard_write_auth_token == "token123"


def test_symbol_config_aceita_leverage_no_limite_maximo() -> None:
    config = SymbolConfig.from_triplet("BTCUSDT:15m:20")
    assert config.leverage == 20


def test_symbol_config_rejeita_leverage_acima_do_limite() -> None:
    with pytest.raises(ValueError, match="inteiro entre 1 e 20"):
        SymbolConfig.from_triplet("BTCUSDT:15m:21")


def test_trade_history_retention_days_default_90(monkeypatch) -> None:
    monkeypatch.setenv("BINANCE_API_KEY", "bot_key")
    monkeypatch.setenv("BINANCE_API_SECRET", "bot_secret")
    monkeypatch.setenv("DASHBOARD_API_KEY", "dash_key")
    monkeypatch.setenv("DASHBOARD_API_SECRET", "dash_secret")

    settings = _build_settings()

    assert settings.trade_history_retention_days == 90


def test_trade_history_retention_days_rejeita_valor_abaixo_de_90(monkeypatch) -> None:
    monkeypatch.setenv("BINANCE_API_KEY", "bot_key")
    monkeypatch.setenv("BINANCE_API_SECRET", "bot_secret")
    monkeypatch.setenv("DASHBOARD_API_KEY", "dash_key")
    monkeypatch.setenv("DASHBOARD_API_SECRET", "dash_secret")
    monkeypatch.setenv("TRADE_HISTORY_RETENTION_DAYS", "30")

    with pytest.raises(ValueError, match="greater than or equal to 90"):
        _build_settings()


def test_ml_support_symbol_timeframes_parse_csv(monkeypatch) -> None:
    monkeypatch.setenv("BINANCE_API_KEY", "bot_key")
    monkeypatch.setenv("BINANCE_API_SECRET", "bot_secret")
    monkeypatch.setenv("DASHBOARD_API_KEY", "dash_key")
    monkeypatch.setenv("DASHBOARD_API_SECRET", "dash_secret")
    monkeypatch.setenv("ML_SUPPORT_SYMBOL_TIMEFRAMES", "btcusdt:15m, ETHUSDT:1h")

    settings = _build_settings()

    assert settings.ml_support_symbol_timeframes == ["BTCUSDT:15m", "ETHUSDT:1h"]


def test_ml_support_symbol_timeframes_rejeita_formato_invalido(monkeypatch) -> None:
    monkeypatch.setenv("BINANCE_API_KEY", "bot_key")
    monkeypatch.setenv("BINANCE_API_SECRET", "bot_secret")
    monkeypatch.setenv("DASHBOARD_API_KEY", "dash_key")
    monkeypatch.setenv("DASHBOARD_API_SECRET", "dash_secret")
    monkeypatch.setenv("ML_SUPPORT_SYMBOL_TIMEFRAMES", "BTCUSDT")

    with pytest.raises(ValueError, match="SYMBOL:TIMEFRAME"):
        _build_settings()
