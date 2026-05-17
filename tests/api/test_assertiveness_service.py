"""Testes do facade de assertividade."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from src.api.services.assertiveness import (
    AssertivenessFacade,
    AssertivenessQuery,
    resolve_period_strategy,
)


def test_strategy_periodo_30d_resolve_janela() -> None:
    strategy = resolve_period_strategy("30d")
    now = datetime(2026, 5, 16, 12, 0, tzinfo=UTC)
    start, end = strategy.resolve(now=now, start=None, end=None)
    assert end == now
    assert (end - start).days == 30


@pytest.mark.asyncio
async def test_facade_calcula_conversao_e_drawdown() -> None:
    repo = AsyncMock()
    repo.get_signals_in_period = AsyncMock(
        return_value=[
            {
                "symbol": "QNTUSDT",
                "detected_at": datetime(2026, 5, 15, tzinfo=UTC),
                "execution_status": "TRADE_OPENED",
            },
            {
                "symbol": "QNTUSDT",
                "detected_at": datetime(2026, 5, 16, tzinfo=UTC),
                "execution_status": "REJECTED_RISK_QTY_ZERO",
            },
        ]
    )
    repo.get_closed_trades_in_period = AsyncMock(
        return_value=[
            {
                "symbol": "QNTUSDT",
                "closed_at": datetime(2026, 5, 15, tzinfo=UTC),
                "pnl_usdt": 10.0,
                "risk_amount": 5.0,
            },
            {
                "symbol": "QNTUSDT",
                "closed_at": datetime(2026, 5, 16, tzinfo=UTC),
                "pnl_usdt": -20.0,
                "risk_amount": 10.0,
            },
        ]
    )
    facade = AssertivenessFacade(repo)
    payload = await facade.build(
        AssertivenessQuery(
            symbol="QNTUSDT",
            timeframe="15m",
            period="30d",
            start=None,
            end=None,
            order_by="assertiveness_pct",
            order_dir="desc",
        )
    )

    assert payload["summary"]["total_signals"] == 2
    assert payload["summary"]["total_trades"] == 2
    assert payload["summary"]["signal_to_trade_conversion_pct"] == 50.0
    assert payload["summary"]["max_drawdown_usdt"] <= 0.0


@pytest.mark.asyncio
async def test_facade_considera_entry_open_no_protection_como_trade_aberto() -> None:
    repo = AsyncMock()
    repo.get_signals_in_period = AsyncMock(
        return_value=[
            {
                "symbol": "MASKUSDT",
                "detected_at": datetime(2026, 5, 16, tzinfo=UTC),
                "execution_status": "ENTRY_OPEN_NO_PROTECTION",
            }
        ]
    )
    repo.get_closed_trades_in_period = AsyncMock(return_value=[])
    facade = AssertivenessFacade(repo)
    payload = await facade.build(
        AssertivenessQuery(
            symbol="MASKUSDT",
            timeframe="15m",
            period="30d",
            start=None,
            end=None,
            order_by="assertiveness_pct",
            order_dir="desc",
        )
    )
    assert payload["summary"]["total_signals"] == 1
    assert payload["summary"]["signal_to_trade_conversion_pct"] == 100.0
