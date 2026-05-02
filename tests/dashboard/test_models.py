"""Testes unitários para os contratos de dados do dashboard."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime

import pytest

from src.dashboard.models import PositionView, build_account_summary


def test_test_001_01_posicao_valida_expoe_todos_os_campos_obrigatorios() -> None:
    """Entrada válida deve produzir PositionView com todos os campos obrigatórios."""
    updated_at = datetime(2026, 5, 1, 12, 30, tzinfo=UTC)

    position = PositionView(
        symbol="BTCUSDT",
        side="LONG",
        quantity=0.25,
        leverage=10,
        entry_price=95000.0,
        mark_price=96000.0,
        unrealized_pnl_usdt=250.0,
        margin_used_usdt=2400.0,
        liquidation_price=87000.0,
        updated_at=updated_at,
    )

    assert asdict(position) == {
        "symbol": "BTCUSDT",
        "side": "LONG",
        "quantity": 0.25,
        "leverage": 10,
        "entry_price": 95000.0,
        "mark_price": 96000.0,
        "unrealized_pnl_usdt": 250.0,
        "margin_used_usdt": 2400.0,
        "liquidation_price": 87000.0,
        "updated_at": updated_at,
    }


def test_test_001_02_lista_de_posicoes_multiplas_gera_totais_corretos() -> None:
    """Múltiplas posições devem gerar resumo agregado coerente com a SPEC."""
    older_update = datetime(2026, 5, 1, 12, 30, tzinfo=UTC)
    latest_update = datetime(2026, 5, 1, 12, 31, tzinfo=UTC)
    positions = [
        PositionView(
            symbol="BTCUSDT",
            side="LONG",
            quantity=0.5,
            leverage=10,
            entry_price=94000.0,
            mark_price=95000.0,
            unrealized_pnl_usdt=500.0,
            margin_used_usdt=4750.0,
            liquidation_price=86000.0,
            updated_at=older_update,
        ),
        PositionView(
            symbol="ETHUSDT",
            side="SHORT",
            quantity=-2.0,
            leverage=8,
            entry_price=1800.0,
            mark_price=1750.0,
            unrealized_pnl_usdt=100.0,
            margin_used_usdt=430.0,
            liquidation_price=None,
            updated_at=latest_update,
        ),
    ]

    summary = build_account_summary(positions, "online")

    assert summary.total_exposure_usdt == pytest.approx(51000.0)
    assert summary.total_margin_used_usdt == pytest.approx(5180.0)
    assert summary.total_unrealized_pnl_usdt == pytest.approx(600.0)
    assert summary.connection_status == "online"
    assert summary.last_update_at == latest_update


def test_updated_at_naive_lanca_value_error() -> None:
    """Datetime naive deve ser rejeitado pelo contrato da posição."""
    with pytest.raises(ValueError, match="updated_at deve ser um datetime com timezone UTC"):
        PositionView(
            symbol="BTCUSDT",
            side="LONG",
            quantity=0.25,
            leverage=10,
            entry_price=95000.0,
            mark_price=96000.0,
            unrealized_pnl_usdt=250.0,
            margin_used_usdt=2400.0,
            liquidation_price=87000.0,
            updated_at=datetime(2026, 5, 1, 12, 30),
        )


def test_position_size_usdt_calculo_correto() -> None:
    """position_size_usdt deve ser calculado como margin_used_usdt * leverage."""
    position = PositionView(
        symbol="BTCUSDT",
        side="LONG",
        quantity=0.25,
        leverage=10,
        entry_price=95000.0,
        mark_price=96000.0,
        unrealized_pnl_usdt=250.0,
        margin_used_usdt=2.7345,
        liquidation_price=87000.0,
        updated_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
    )
    assert position.position_size_usdt == pytest.approx(27.345)


def test_roi_adjusted_pct_calculo_correto() -> None:
    """roi_adjusted_pct deve ser calculado como (unrealized_pnl_usdt / position_size_usdt) * 100."""
    position = PositionView(
        symbol="BTCUSDT",
        side="LONG",
        quantity=0.25,
        leverage=10,
        entry_price=95000.0,
        mark_price=96000.0,
        unrealized_pnl_usdt=-21.0,
        margin_used_usdt=2.7345,
        liquidation_price=87000.0,
        updated_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
    )
    assert position.roi_adjusted_pct == pytest.approx(-76.8, abs=0.1)


def test_position_size_usdt_dados_invalidos_retorna_none() -> None:
    """Se margin_used_usdt < 0 ou leverage <= 0, position_size_usdt deve retornar None."""
    # leverage <= 0
    position = PositionView(
        symbol="BTCUSDT",
        side="LONG",
        quantity=0.25,
        leverage=0,
        entry_price=95000.0,
        mark_price=96000.0,
        unrealized_pnl_usdt=250.0,
        margin_used_usdt=2400.0,
        liquidation_price=87000.0,
        updated_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
    )
    assert position.position_size_usdt is None

    # margin_used_usdt < 0
    position2 = PositionView(
        symbol="BTCUSDT",
        side="LONG",
        quantity=0.25,
        leverage=10,
        entry_price=95000.0,
        mark_price=96000.0,
        unrealized_pnl_usdt=250.0,
        margin_used_usdt=-100.0,
        liquidation_price=87000.0,
        updated_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
    )
    assert position2.position_size_usdt is None


def test_roi_adjusted_pct_position_size_zero_retorna_none() -> None:
    """Se position_size_usdt <= 0, roi_adjusted_pct deve retornar None."""
    position = PositionView(
        symbol="BTCUSDT",
        side="LONG",
        quantity=0.25,
        leverage=0,  # faz position_size_usdt = None
        entry_price=95000.0,
        mark_price=96000.0,
        unrealized_pnl_usdt=-21.0,
        margin_used_usdt=2400.0,
        liquidation_price=87000.0,
        updated_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
    )
    assert position.roi_adjusted_pct is None
