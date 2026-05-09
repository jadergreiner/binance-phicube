"""Testes unitários da análise de cenário de posições do dashboard."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.dashboard.analysis import build_market_analysis
from src.dashboard.models import PositionView


def _make_position(
    *,
    symbol: str,
    side: str,
    quantity: float,
    leverage: int,
    entry_price: float,
    mark_price: float,
    unrealized_pnl_usdt: float,
    margin_used_usdt: float,
    updated_at: datetime,
) -> PositionView:
    return PositionView(
        symbol=symbol,
        side=side,
        quantity=quantity,
        leverage=leverage,
        entry_price=entry_price,
        mark_price=mark_price,
        unrealized_pnl_usdt=unrealized_pnl_usdt,
        margin_used_usdt=margin_used_usdt,
        liquidation_price=None,
        updated_at=updated_at,
    )


def test_build_market_analysis_sem_posicoes_retorna_bias_neutral() -> None:
    analysis = build_market_analysis([])

    assert analysis.bias.direction == "NEUTRAL"
    assert analysis.bias.confidence == "low"
    assert analysis.bias.score == 0.0
    assert len(analysis.opportunities) == 1
    assert analysis.opportunities[0].action == "HOLD"
    assert analysis.opportunities[0].direction == "NEUTRAL"
    assert analysis.bias_views.active == "allocation"
    assert len(analysis.bias_views.views) == 3


def test_build_market_analysis_identifica_bias_long_e_oportunidade_add() -> None:
    positions = [
        _make_position(
            symbol="BTCUSDT",
            side="LONG",
            quantity=0.5,
            leverage=10,
            entry_price=95000.0,
            mark_price=96000.0,
            unrealized_pnl_usdt=250.0,
            margin_used_usdt=2400.0,
            updated_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
        )
    ]

    analysis = build_market_analysis(positions)

    assert analysis.bias.direction == "LONG"
    assert analysis.bias.confidence == "high"
    assert analysis.bias.score == 1.0
    assert analysis.opportunities[0].symbol == "BTCUSDT"
    assert analysis.opportunities[0].action == "ADD"
    assert analysis.opportunities[0].direction == "LONG"
    assert analysis.bias_views.views[0].id == "allocation"
    assert analysis.bias_views.views[0].direction == "LONG"


def test_build_market_analysis_bias_short_reduz_long_exposicao() -> None:
    positions = [
        _make_position(
            symbol="BTCUSDT",
            side="SHORT",
            quantity=-1.0,
            leverage=8,
            entry_price=1700.0,
            mark_price=1650.0,
            unrealized_pnl_usdt=100.0,
            margin_used_usdt=1000.0,
            updated_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
        ),
        _make_position(
            symbol="ETHUSDT",
            side="LONG",
            quantity=0.3,
            leverage=10,
            entry_price=1800.0,
            mark_price=1815.0,
            unrealized_pnl_usdt=50.0,
            margin_used_usdt=540.0,
            updated_at=datetime(2026, 5, 1, 12, 31, tzinfo=UTC),
        ),
    ]

    analysis = build_market_analysis(positions)

    assert analysis.bias.direction == "SHORT"
    assert analysis.bias.confidence == "low"
    assert analysis.bias.score == pytest.approx(0.19402985074626866)
    assert analysis.opportunities[0].direction == "SHORT"
    assert analysis.opportunities[0].action == "ADD"
    assert analysis.opportunities[1].action == "REDUCE"


def test_build_market_analysis_identifica_bias_short_e_oportunidade_add() -> None:
    positions = [
        _make_position(
            symbol="BTCUSDT",
            side="LONG",
            quantity=0.5,
            leverage=10,
            entry_price=95000.0,
            mark_price=96000.0,
            unrealized_pnl_usdt=250.0,
            margin_used_usdt=2400.0,
            updated_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
        ),
        _make_position(
            symbol="ETHUSDT",
            side="SHORT",
            quantity=-0.5,
            leverage=10,
            entry_price=1800.0,
            mark_price=1790.0,
            unrealized_pnl_usdt=50.0,
            margin_used_usdt=5000.0,
            updated_at=datetime(2026, 5, 1, 12, 31, tzinfo=UTC),
        ),
    ]

    analysis = build_market_analysis(positions)

    assert analysis.bias.direction == "SHORT"
    assert analysis.bias.confidence == "medium"
    assert analysis.bias.score == pytest.approx(0.35135135135135137)
    assert analysis.opportunities[0].direction == "SHORT"
    assert analysis.opportunities[0].action == "ADD"
    assert analysis.opportunities[1].action == "REDUCE"


def test_build_market_analysis_ignora_exposicao_invalida() -> None:
    positions = [
        _make_position(
            symbol="BTCUSDT",
            side="LONG",
            quantity=0.5,
            leverage=10,
            entry_price=95000.0,
            mark_price=96000.0,
            unrealized_pnl_usdt=250.0,
            margin_used_usdt=2400.0,
            updated_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
        ),
        _make_position(
            symbol="ETHUSDT",
            side="SHORT",
            quantity=-0.5,
            leverage=0,
            entry_price=1800.0,
            mark_price=1790.0,
            unrealized_pnl_usdt=-50.0,
            margin_used_usdt=500.0,
            updated_at=datetime(2026, 5, 1, 12, 31, tzinfo=UTC),
        ),
    ]

    analysis = build_market_analysis(positions)

    assert analysis.bias.direction == "LONG"
    assert analysis.bias.confidence == "high"
    assert analysis.bias.score == 1.0
    assert analysis.opportunities[0].symbol == "BTCUSDT"
    assert analysis.opportunities[0].action == "ADD"


def test_build_market_analysis_sinaliza_divergencia_entre_visoes() -> None:
    positions = [
        _make_position(
            symbol="LONGPOS",
            side="LONG",
            quantity=1.0,
            leverage=10,
            entry_price=100.0,
            mark_price=95.0,
            unrealized_pnl_usdt=-50.0,
            margin_used_usdt=10.0,
            updated_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
        ),
        _make_position(
            symbol="SHORTPOS",
            side="SHORT",
            quantity=-1.0,
            leverage=10,
            entry_price=100.0,
            mark_price=110.0,
            unrealized_pnl_usdt=50.0,
            margin_used_usdt=10.0,
            updated_at=datetime(2026, 5, 1, 12, 31, tzinfo=UTC),
        ),
    ]
    analysis = build_market_analysis(positions)
    assert analysis.bias.direction == "NEUTRAL"
    assert analysis.bias_views.divergence.has_divergence is True
    assert "allocation=NEUTRAL" in analysis.bias_views.divergence.summary
