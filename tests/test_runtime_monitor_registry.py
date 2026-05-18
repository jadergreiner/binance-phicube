from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from src.config.settings import SymbolConfig
from src.exchange.binance_client import InsufficientLiquidityError
from src.main import RuntimeMonitorRegistry
from src.strategies.phicube_strategy import PhicubeStrategy
from src.strategies.williams_strategy import WilliamsStrategy


@pytest.mark.asyncio
async def test_runtime_monitor_skips_symbol_with_insufficient_liquidity():
    client = Mock()
    client.validate_market_liquidity = AsyncMock(
        side_effect=InsufficientLiquidityError(
            "XPDUSDT: volume_24h baixo", reason_code="insufficient_volume"
        )
    )
    client.set_leverage = AsyncMock()

    registry = RuntimeMonitorRegistry(
        settings=SimpleNamespace(
            risk_per_trade_pct=1.0,
            max_capital_allocation_pct=20.0,
            max_open_positions=3,
            warmup_candles=200,
            plugin_timeout=30.0,
            default_strategy="williams",
            symbol_strategy_map={},
            risk_reward_ratio=2.0,
        ),
        client=client,
        repo=Mock(),
        notifier=Mock(),
        router=AsyncMock(),
    )

    await registry.add(SymbolConfig(symbol="XPDUSDT", timeframe="15m", leverage=10))

    assert registry.monitor_count == 0
    client.set_leverage.assert_not_called()


def test_strategy_routing_keeps_existing_behavior_when_phicube_disabled() -> None:
    registry = RuntimeMonitorRegistry(
        settings=SimpleNamespace(
            plugin_timeout=30.0,
            default_strategy="williams",
            symbol_strategy_map={"BTCUSDT": "williams"},
            phicube_enabled=False,
            symbol_timeframes=[SymbolConfig(symbol="BTCUSDT", timeframe="15m", leverage=5)],
            risk_reward_ratio=2.0,
        ),
        client=Mock(),
        repo=Mock(),
        notifier=Mock(),
        router=AsyncMock(),
    )

    default_strategy, strategy_map = registry._resolve_strategy_routing()

    assert default_strategy == "williams"
    assert strategy_map == {"BTCUSDT": "williams"}


def test_strategy_routing_enables_phicube_when_flag_is_true() -> None:
    registry = RuntimeMonitorRegistry(
        settings=SimpleNamespace(
            plugin_timeout=30.0,
            default_strategy="williams",
            symbol_strategy_map={"BTCUSDT": "williams"},
            phicube_enabled=True,
            phicube_mode="shadow",
            symbol_timeframes=[
                SymbolConfig(symbol="BTCUSDT", timeframe="15m", leverage=5),
                SymbolConfig(symbol="ETHUSDT", timeframe="1h", leverage=3),
            ],
            risk_reward_ratio=2.0,
        ),
        client=Mock(),
        repo=Mock(),
        notifier=Mock(),
        router=AsyncMock(),
    )

    default_strategy, strategy_map = registry._resolve_strategy_routing()

    assert default_strategy == "phicube"
    assert strategy_map["BTCUSDT"] == "phicube"
    assert strategy_map["ETHUSDT"] == "phicube"


def test_make_signal_engine_chain_uses_williams_only_when_phicube_disabled() -> None:
    registry = RuntimeMonitorRegistry(
        settings=SimpleNamespace(
            plugin_timeout=30.0,
            default_strategy="williams",
            symbol_strategy_map={"BTCUSDT": "williams"},
            phicube_enabled=False,
            symbol_timeframes=[SymbolConfig(symbol="BTCUSDT", timeframe="15m", leverage=5)],
            risk_reward_ratio=2.0,
        ),
        client=Mock(),
        repo=Mock(),
        notifier=Mock(),
        router=AsyncMock(),
    )
    registry._plugin_registry.register("williams", WilliamsStrategy())
    registry._plugin_registry.register("phicube", PhicubeStrategy())

    engine = registry._make_signal_engine()
    chain = engine._build_chain("BTCUSDT")

    assert [name for name, _handler in chain] == ["williams"]


def test_make_signal_engine_chain_uses_phicube_and_fallback_when_enabled() -> None:
    registry = RuntimeMonitorRegistry(
        settings=SimpleNamespace(
            plugin_timeout=30.0,
            default_strategy="williams",
            symbol_strategy_map={},
            phicube_enabled=True,
            phicube_mode="shadow",
            symbol_timeframes=[SymbolConfig(symbol="BTCUSDT", timeframe="15m", leverage=5)],
            risk_reward_ratio=2.0,
        ),
        client=Mock(),
        repo=Mock(),
        notifier=Mock(),
        router=AsyncMock(),
    )
    registry._plugin_registry.register("williams", WilliamsStrategy())
    registry._plugin_registry.register("phicube", PhicubeStrategy())

    engine = registry._make_signal_engine()
    chain = engine._build_chain("BTCUSDT")

    assert [name for name, _handler in chain] == ["phicube", "williams"]
