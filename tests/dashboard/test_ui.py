"""Testes unitários da camada de apresentação do dashboard."""

from __future__ import annotations

from datetime import UTC, datetime

from src.dashboard.models import AccountSummary, PositionView
from src.dashboard.ui import (
    TABLE_COLUMNS,
    DashboardSnapshotBuilder,
    build_dashboard_snapshot,
    serialize_account_summary,
)


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
    liquidation_price: float | None,
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
        liquidation_price=liquidation_price,
        updated_at=updated_at,
    )


def test_snapshot_renderiza_tabela_com_campos_obrigatorios() -> None:
    older_update = datetime(2026, 5, 1, 12, 30, tzinfo=UTC)
    latest_update = datetime(2026, 5, 1, 12, 31, tzinfo=UTC)
    positions = [
        _make_position(
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
        _make_position(
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

    snapshot = build_dashboard_snapshot(positions, "online")

    assert snapshot["readonly"] is True
    assert set(snapshot) == {
        "alert",
        "analysis",
        "banner",
        "readonly",
        "status_indicator",
        "summary",
        "table",
    }
    assert snapshot["status_indicator"] == {
        "connection_status": "online",
        "label": "online",
        "data_reliable": True,
    }
    assert snapshot["banner"] == {
        "visible": False,
        "level": "info",
        "title": "",
        "message": "",
    }
    assert snapshot["alert"] == {
        "visible": False,
        "kind": "sound+visual",
        "message": "",
    }

    table = snapshot["table"]

    assert table["columns"] == list(TABLE_COLUMNS)
    assert table["rows"] == [
        {
            "symbol": "BTCUSDT",
            "side": "LONG",
            "quantity": 0.5,
            "leverage": 10,
            "entry_price": 94000.0,
            "mark_price": 95000.0,
            "unrealized_pnl_usdt": 500.0,
            "margin_used_usdt": 4750.0,
            "liquidation_price": 86000.0,
            "updated_at": "2026-05-01 12:30:00 UTC",
        },
        {
            "symbol": "ETHUSDT",
            "side": "SHORT",
            "quantity": -2.0,
            "leverage": 8,
            "entry_price": 1800.0,
            "mark_price": 1750.0,
            "unrealized_pnl_usdt": 100.0,
            "margin_used_usdt": 430.0,
            "liquidation_price": "—",
            "updated_at": "2026-05-01 12:31:00 UTC",
        },
    ]


def test_serialize_account_summary_renderiza_totais_e_timestamp_legivel() -> None:
    summary = AccountSummary(
        total_exposure_usdt=51000.0,
        total_margin_used_usdt=5180.0,
        total_unrealized_pnl_usdt=600.0,
        connection_status="degraded",
        last_update_at=datetime(2026, 5, 1, 12, 31, tzinfo=UTC),
        account_equity_usdt=17000.0,
        exposure_to_equity_ratio=3.0,
    )

    assert serialize_account_summary(summary) == {
        "total_exposure_usdt": 51000.0,
        "total_margin_used_usdt": 5180.0,
        "total_unrealized_pnl_usdt": 600.0,
        "account_equity_usdt": 17000.0,
        "exposure_to_equity_ratio": 3.0,
        "connection_status": "degraded",
        "last_update_at": "2026-05-01 12:31:00 UTC",
    }


def test_snapshot_mascara_campos_sensiveis_e_exibe_banner_em_modo_degradado() -> None:
    positions = [
        _make_position(
            symbol="BTCUSDT",
            side="LONG",
            quantity=0.5,
            leverage=10,
            entry_price=94000.0,
            mark_price=95000.0,
            unrealized_pnl_usdt=500.0,
            margin_used_usdt=4750.0,
            liquidation_price=86000.0,
            updated_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
        )
    ]

    snapshot = build_dashboard_snapshot(positions, "degraded", previous_status="online")

    assert snapshot["summary"]["connection_status"] == "degraded"
    assert snapshot["summary"]["last_update_at"] == "2026-05-01 12:30:00 UTC"
    assert snapshot["table"]["rows"] == [
        {
            "symbol": "BTCUSDT",
            "side": "LONG",
            "quantity": 0.5,
            "leverage": 10,
            "entry_price": 94000.0,
            "mark_price": "—",
            "unrealized_pnl_usdt": "—",
            "margin_used_usdt": 4750.0,
            "liquidation_price": 86000.0,
            "updated_at": "2026-05-01 12:30:00 UTC",
        }
    ]
    assert snapshot["banner"] == {
        "visible": True,
        "level": "warning",
        "title": "Modo degradado ativo",
        "message": (
            "Dados nao confiaveis: o painel esta em modo degradado ate a reconciliacao "
            "ser concluida."
        ),
    }
    assert snapshot["alert"] == {
        "visible": True,
        "kind": "sound+visual",
        "message": (
            "ALERTA: painel entrou em modo degradado. Dados nao confiaveis ate a reconciliacao."
        ),
    }


def test_builder_dispara_alerta_uma_vez_por_transicao_para_degradado() -> None:
    builder = DashboardSnapshotBuilder()
    positions = [
        _make_position(
            symbol="ETHUSDT",
            side="SHORT",
            quantity=-1.0,
            leverage=8,
            entry_price=1800.0,
            mark_price=1750.0,
            unrealized_pnl_usdt=100.0,
            margin_used_usdt=430.0,
            liquidation_price=None,
            updated_at=datetime(2026, 5, 1, 12, 31, tzinfo=UTC),
        )
    ]

    online_snapshot = builder.build_snapshot(positions, "online")
    degraded_snapshot = builder.build_snapshot(positions, "degraded")
    degraded_snapshot_repeated = builder.build_snapshot(positions, "degraded")
    recovered_snapshot = builder.build_snapshot(positions, "online")

    assert online_snapshot["alert"]["visible"] is False
    assert degraded_snapshot["alert"] == {
        "visible": True,
        "kind": "sound+visual",
        "message": (
            "ALERTA: painel entrou em modo degradado. Dados nao confiaveis ate a reconciliacao."
        ),
    }
    assert degraded_snapshot_repeated["alert"] == {
        "visible": False,
        "kind": "sound+visual",
        "message": "",
    }
    assert recovered_snapshot["status_indicator"] == {
        "connection_status": "online",
        "label": "online",
        "data_reliable": True,
    }
    assert recovered_snapshot["banner"] == {
        "visible": False,
        "level": "info",
        "title": "",
        "message": "",
    }
