"""
Testes de conformidade SPEC_018 — SymbolConfig e Settings.

Cobre:
- Parse de triplet válido
- Triplet com formato inválido (< 3 partes)
- Triplet com leverage zero ou negativo
- Settings.symbol_timeframes retorna lista de SymbolConfig
- Gate de commodities: ValidationError sem backtest validado
- Gate de commodities: OK com backtest validado
- TradingMonitor._interval derivado do timeframe
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.config.settings import SymbolConfig

# ─── SymbolConfig.from_triplet ────────────────────────────────────────────────


def test_from_triplet_valido() -> None:
    cfg = SymbolConfig.from_triplet("BTCUSDT:15m:5")
    assert cfg.symbol == "BTCUSDT"
    assert cfg.timeframe == "15m"
    assert cfg.leverage == 5


def test_from_triplet_uppercase_symbol() -> None:
    cfg = SymbolConfig.from_triplet("btcusdt:15m:5")
    assert cfg.symbol == "BTCUSDT"


def test_from_triplet_formato_invalido_duas_partes() -> None:
    with pytest.raises(ValueError, match="formato esperado"):
        SymbolConfig.from_triplet("BTCUSDT:15m")


def test_from_triplet_formato_invalido_uma_parte() -> None:
    with pytest.raises(ValueError, match="formato esperado"):
        SymbolConfig.from_triplet("BTCUSDT")


def test_from_triplet_leverage_zero() -> None:
    with pytest.raises(ValueError, match="Leverage inválida"):
        SymbolConfig.from_triplet("BTCUSDT:15m:0")


def test_from_triplet_leverage_nao_numerico() -> None:
    with pytest.raises(ValueError, match="Leverage inválida"):
        SymbolConfig.from_triplet("BTCUSDT:15m:abc")


def test_from_triplet_commodity_1h_3x() -> None:
    cfg = SymbolConfig.from_triplet("XPTUSDT:1h:3")
    assert cfg.symbol == "XPTUSDT"
    assert cfg.timeframe == "1h"
    assert cfg.leverage == 3


# ─── Settings.symbol_timeframes ───────────────────────────────────────────────


def _make_settings(**kwargs):
    from src.config.settings import Settings

    base = dict(
        binance_api_key="key",
        binance_api_secret="secret",
        dashboard_api_key="dkey",
        dashboard_api_secret="dsecret",
    )
    base.update(kwargs)
    return Settings(**base)


def test_settings_symbol_timeframes_parse_csv() -> None:
    s = _make_settings(symbol_timeframes="BTCUSDT:15m:5,ETHUSDT:15m:5")
    assert len(s.symbol_timeframes) == 2
    assert s.symbol_timeframes[0].symbol == "BTCUSDT"
    assert s.symbol_timeframes[1].symbol == "ETHUSDT"


def test_settings_commodity_sem_gate_levanta() -> None:
    with pytest.raises(ValidationError, match="backtest não validado"):
        _make_settings(
            symbol_timeframes="XPTUSDT:1h:3",
            commodities_backtest_validated=False,
        )


def test_settings_commodity_com_gate_ok() -> None:
    s = _make_settings(
        symbol_timeframes="XPTUSDT:1h:3,COPPERUSDT:1h:3",
        commodities_backtest_validated=True,
    )
    symbols = [c.symbol for c in s.symbol_timeframes]
    assert "XPTUSDT" in symbols
    assert "COPPERUSDT" in symbols


def test_settings_crypto_sem_gate_ok() -> None:
    s = _make_settings(symbol_timeframes="BTCUSDT:15m:5,ETHUSDT:15m:5")
    assert len(s.symbol_timeframes) == 2


# ─── TradingMonitor._interval ─────────────────────────────────────────────────


def test_trading_monitor_intervalo_15m() -> None:
    from unittest.mock import MagicMock

    from src.main import TradingMonitor

    cfg = SymbolConfig(symbol="BTCUSDT", timeframe="15m", leverage=5)
    monitor = TradingMonitor(
        config=cfg,
        client=MagicMock(),
        repo=MagicMock(),
        signal_engine=MagicMock(),
        risk_manager=MagicMock(),
        order_manager=MagicMock(),
        notifier=MagicMock(),
        max_open_positions=3,
        warmup_candles=200,
    )
    assert monitor._interval == 900


def test_trading_monitor_intervalo_1h() -> None:
    from unittest.mock import MagicMock

    from src.main import TradingMonitor

    cfg = SymbolConfig(symbol="XPTUSDT", timeframe="1h", leverage=3)
    monitor = TradingMonitor(
        config=cfg,
        client=MagicMock(),
        repo=MagicMock(),
        signal_engine=MagicMock(),
        risk_manager=MagicMock(),
        order_manager=MagicMock(),
        notifier=MagicMock(),
        max_open_positions=3,
        warmup_candles=200,
    )
    assert monitor._interval == 3600


def test_trading_monitor_intervalo_timeframe_desconhecido() -> None:
    from unittest.mock import MagicMock

    from src.main import TradingMonitor

    cfg = SymbolConfig(symbol="XPTUSDT", timeframe="99x", leverage=3)
    monitor = TradingMonitor(
        config=cfg,
        client=MagicMock(),
        repo=MagicMock(),
        signal_engine=MagicMock(),
        risk_manager=MagicMock(),
        order_manager=MagicMock(),
        notifier=MagicMock(),
        max_open_positions=3,
        warmup_candles=200,
    )
    assert monitor._interval == 300
