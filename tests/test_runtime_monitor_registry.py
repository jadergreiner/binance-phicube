from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from src.config.settings import SymbolConfig
from src.exchange.binance_client import InsufficientLiquidityError
from src.main import RuntimeMonitorRegistry


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
