"""Camada mínima de apresentação para o painel de posições."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from src.dashboard.analysis import MarketAnalysis, MarketBias, TradeOpportunity, build_market_analysis
from src.dashboard.models import (
    AccountSummary,
    ConnectionStatus,
    PositionView,
    build_account_summary,
)

TABLE_COLUMNS = (
    "symbol",
    "side",
    "quantity",
    "leverage",
    "entry_price",
    "mark_price",
    "unrealized_pnl_usdt",
    "margin_used_usdt",
    "liquidation_price",
    "updated_at",
)

_MASKED_VALUE = "—"
_UNRELIABLE_STATUSES = {"degraded", "offline", "cached"}
_STATUS_LABELS: dict[ConnectionStatus, str] = {
    "online": "online",
    "degraded": "degraded",
    "offline": "offline",
    "cached": "cached",
}
_BANNER_CONTENT: dict[ConnectionStatus, dict[str, str]] = {
    "degraded": {
        "level": "warning",
        "title": "Modo degradado ativo",
        "message": (
            "Dados nao confiaveis: o painel esta em modo degradado ate a reconciliacao "
            "ser concluida."
        ),
    },
    "offline": {
        "level": "critical",
        "title": "Painel offline",
        "message": (
            "Sem conexao ativa com a fonte de dados. Ultimo timestamp visivel apenas "
            "como referencia."
        ),
    },
    "cached": {
        "level": "warning",
        "title": "Snapshot em cache",
        "message": (
            "Dados nao confiaveis: exibicao baseada em cache ate sincronizar com a " "Binance."
        ),
    },
}


@dataclass(slots=True)
class DashboardSnapshotBuilder:
    """Mantem estado minimo para disparar alerta unico na transicao de degradacao."""

    _last_status: ConnectionStatus | None = None

    def build_snapshot(
        self,
        positions: list[PositionView],
        status: ConnectionStatus,
    ) -> dict[str, object]:
        snapshot = _compose_dashboard_snapshot(
            positions,
            status,
            previous_status=self._last_status,
        )
        self._last_status = status
        return snapshot


def _format_timestamp(value: datetime) -> str:
    """Converte timestamps UTC para um formato legível no painel."""
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def _mask_market_fields(status: ConnectionStatus, *, value: float) -> float | str:
    if status in _UNRELIABLE_STATUSES:
        return _MASKED_VALUE
    return value


def _build_status_indicator(status: ConnectionStatus) -> dict[str, object]:
    return {
        "connection_status": status,
        "label": _STATUS_LABELS[status],
        "data_reliable": status == "online",
    }


def _build_banner(status: ConnectionStatus) -> dict[str, object]:
    if status == "online":
        return {
            "visible": False,
            "level": "info",
            "title": "",
            "message": "",
        }

    content = _BANNER_CONTENT[status]
    return {
        "visible": True,
        "level": content["level"],
        "title": content["title"],
        "message": content["message"],
    }


def _build_alert(
    status: ConnectionStatus,
    *,
    previous_status: ConnectionStatus | None,
) -> dict[str, object]:
    is_transition_to_degraded = (
        previous_status is not None and previous_status != "degraded" and status == "degraded"
    )
    return {
        "visible": is_transition_to_degraded,
        "kind": "sound+visual",
        "message": (
            "ALERTA: painel entrou em modo degradado. Dados nao confiaveis ate a reconciliacao."
            if is_transition_to_degraded
            else ""
        ),
    }


def serialize_position_table(
    positions: list[PositionView],
    status: ConnectionStatus = "online",
) -> dict[str, object]:
    """Serializa as posições abertas para uma tabela renderizável."""
    rows = [
        {
            "symbol": position.symbol,
            "side": position.side,
            "quantity": position.quantity,
            "leverage": position.leverage,
            "entry_price": position.entry_price,
            "mark_price": _mask_market_fields(status, value=position.mark_price),
            "unrealized_pnl_usdt": _mask_market_fields(
                status,
                value=position.unrealized_pnl_usdt,
            ),
            "margin_used_usdt": position.margin_used_usdt,
            "liquidation_price": (
                position.liquidation_price
                if position.liquidation_price is not None
                else _MASKED_VALUE
            ),
            "updated_at": _format_timestamp(position.updated_at),
        }
        for position in positions
    ]
    return {"columns": list(TABLE_COLUMNS), "rows": rows}


def serialize_account_summary(summary: AccountSummary) -> dict[str, object]:
    """Serializa o resumo agregado para um card renderizável."""
    return {
        "total_exposure_usdt": summary.total_exposure_usdt,
        "total_margin_used_usdt": summary.total_margin_used_usdt,
        "total_unrealized_pnl_usdt": summary.total_unrealized_pnl_usdt,
        "connection_status": summary.connection_status,
        "last_update_at": _format_timestamp(summary.last_update_at),
    }


def serialize_market_bias(market_bias: MarketBias) -> dict[str, object]:
    return {
        "direction": market_bias.direction,
        "confidence": market_bias.confidence,
        "score": market_bias.score,
        "reason": market_bias.reason,
    }


def serialize_trade_opportunity(opportunity: TradeOpportunity) -> dict[str, object]:
    return {
        "symbol": opportunity.symbol,
        "direction": opportunity.direction,
        "action": opportunity.action,
        "rationale": opportunity.rationale,
        "exposure_usdt": opportunity.exposure_usdt,
    }


def serialize_market_analysis(market_analysis: MarketAnalysis) -> dict[str, object]:
    return {
        "bias": serialize_market_bias(market_analysis.bias),
        "opportunities": [
            serialize_trade_opportunity(opportunity)
            for opportunity in market_analysis.opportunities
        ],
    }


def build_dashboard_snapshot(
    positions: list[PositionView],
    status: ConnectionStatus,
    *,
    previous_status: ConnectionStatus | None = None,
) -> dict[str, object]:
    """Monta um snapshot de leitura pronto para renderização no dashboard."""
    return _compose_dashboard_snapshot(positions, status, previous_status=previous_status)


def _compose_dashboard_snapshot(
    positions: list[PositionView],
    status: ConnectionStatus,
    *,
    previous_status: ConnectionStatus | None,
) -> dict[str, object]:
    """Centraliza a montagem do snapshot da UI com status, banner e alerta."""
    summary = build_account_summary(positions, status)
    market_analysis = build_market_analysis(positions)
    return {
        "readonly": True,
        "summary": serialize_account_summary(summary),
        "analysis": serialize_market_analysis(market_analysis),
        "table": serialize_position_table(positions, status),
        "status_indicator": _build_status_indicator(status),
        "banner": _build_banner(status),
        "alert": _build_alert(status, previous_status=previous_status),
    }


__all__ = [
    "DashboardSnapshotBuilder",
    "TABLE_COLUMNS",
    "build_dashboard_snapshot",
    "serialize_account_summary",
    "serialize_position_table",
    "serialize_market_analysis",
]
