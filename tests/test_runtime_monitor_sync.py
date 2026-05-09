from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.config.settings import SymbolConfig
from src.main import RuntimeMonitorSyncTask


@pytest.mark.asyncio
async def test_sync_once_mescla_base_com_approved() -> None:
    settings = SimpleNamespace(
        symbol_timeframes=[
            SymbolConfig(symbol="BTCUSDT", timeframe="15m", leverage=10),
            SymbolConfig(symbol="ETHUSDT", timeframe="15m", leverage=10),
        ],
        runtime_monitor_auto_sync_interval_seconds=30,
    )

    sessions = [
        {"status": "APPROVED", "symbol": "ATOMUSDT", "timeframe": "15m", "leverage": 7},
        {"status": "BACKTESTED", "symbol": "SOLUSDT", "timeframe": "1h", "leverage": 5},
    ]

    class _Repo:
        async def list_onboarding_sessions(self):
            return sessions

    class _Registry:
        def __init__(self) -> None:
            self.reconciled: list[SymbolConfig] = []
            self.monitor_count = 0

        async def reconcile(self, desired_configs: list[SymbolConfig]) -> None:
            self.reconciled = desired_configs
            self.monitor_count = len(desired_configs)

        def active_pairs(self):
            return [(c.symbol, c.timeframe, c.leverage) for c in self.reconciled]

    registry = _Registry()
    task = RuntimeMonitorSyncTask(settings=settings, repo=_Repo(), registry=registry)
    await task.sync_once()

    pairs = {(cfg.symbol, cfg.timeframe, cfg.leverage) for cfg in registry.reconciled}
    assert ("BTCUSDT", "15m", 10) in pairs
    assert ("ETHUSDT", "15m", 10) in pairs
    assert ("ATOMUSDT", "15m", 7) in pairs
    assert all(item[0] != "SOLUSDT" for item in pairs)


@pytest.mark.asyncio
async def test_sync_once_approved_substitui_base_mesmo_symbol_timeframe() -> None:
    settings = SimpleNamespace(
        symbol_timeframes=[SymbolConfig(symbol="BTCUSDT", timeframe="15m", leverage=10)],
        runtime_monitor_auto_sync_interval_seconds=30,
    )

    sessions = [
        {"status": "APPROVED", "symbol": "BTCUSDT", "timeframe": "15m", "leverage": 3},
    ]

    class _Repo:
        async def list_onboarding_sessions(self):
            return sessions

    class _Registry:
        def __init__(self) -> None:
            self.reconciled: list[SymbolConfig] = []
            self.monitor_count = 0

        async def reconcile(self, desired_configs: list[SymbolConfig]) -> None:
            self.reconciled = desired_configs
            self.monitor_count = len(desired_configs)

        def active_pairs(self):
            return [(c.symbol, c.timeframe, c.leverage) for c in self.reconciled]

    registry = _Registry()
    task = RuntimeMonitorSyncTask(settings=settings, repo=_Repo(), registry=registry)
    await task.sync_once()

    assert len(registry.reconciled) == 1
    cfg = registry.reconciled[0]
    assert cfg.symbol == "BTCUSDT"
    assert cfg.timeframe == "15m"
    assert cfg.leverage == 3
