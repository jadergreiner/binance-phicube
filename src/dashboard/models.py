"""Modelos de leitura do painel de posições em tempo real."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, get_args

ConnectionStatus = Literal["online", "degraded", "offline", "cached"]

_CONNECTION_STATUS_VALUES = set(get_args(ConnectionStatus))


def _validate_utc_datetime(value: datetime, *, field_name: str) -> datetime:
    """Valida que o datetime recebido é timezone-aware e está em UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} deve ser um datetime com timezone UTC")

    if value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} deve estar em UTC")

    return value


@dataclass(slots=True, frozen=True)
class PositionView:
    """Contrato de leitura de uma posição aberta no painel."""

    symbol: str
    side: str
    quantity: float
    leverage: int
    entry_price: float
    mark_price: float
    unrealized_pnl_usdt: float
    margin_used_usdt: float
    liquidation_price: float | None
    updated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "updated_at",
            _validate_utc_datetime(self.updated_at, field_name="updated_at"),
        )

    @property
    def position_size_usdt(self) -> float | None:
        """Calcula o tamanho da posição em USDT (margem usada * alavancagem)."""
        if self.margin_used_usdt < 0 or self.leverage <= 0:
            return None
        return self.margin_used_usdt * self.leverage

    @property
    def roi_adjusted_pct(self) -> float | None:
        """Calcula o ROI ajustado pela alavancagem em porcentagem."""
        size = self.position_size_usdt
        if size is None or size <= 0:
            return None
        return (self.unrealized_pnl_usdt / size) * 100


@dataclass(slots=True, frozen=True)
class AccountSummary:
    """Resumo agregado das posições exibidas no painel."""

    total_exposure_usdt: float
    total_margin_used_usdt: float
    total_unrealized_pnl_usdt: float
    connection_status: ConnectionStatus
    last_update_at: datetime

    def __post_init__(self) -> None:
        if self.connection_status not in _CONNECTION_STATUS_VALUES:
            raise ValueError("connection_status deve ser um de: online, degraded, offline, cached")

        object.__setattr__(
            self,
            "last_update_at",
            _validate_utc_datetime(self.last_update_at, field_name="last_update_at"),
        )


def build_account_summary(
    positions: list[PositionView], status: ConnectionStatus
) -> AccountSummary:
    """Monta o resumo agregado do painel com base nas posições abertas."""
    if status not in _CONNECTION_STATUS_VALUES:
        raise ValueError("status deve ser um de: online, degraded, offline, cached")

    def _extract_position_size(position: PositionView) -> float | None:
        size = getattr(position, "position_size_usdt", None)
        if size is not None:
            return size
        try:
            if position.margin_used_usdt < 0 or position.leverage <= 0:
                return None
            return position.margin_used_usdt * position.leverage
        except Exception:
            return None

    total_exposure_usdt = sum(
        _extract_position_size(position) or 0.0 for position in positions
    )
    total_margin_used_usdt = sum(position.margin_used_usdt for position in positions)
    total_unrealized_pnl_usdt = sum(position.unrealized_pnl_usdt for position in positions)
    last_update_at = max(
        (position.updated_at for position in positions),
        default=datetime.now(UTC),
    )

    return AccountSummary(
        total_exposure_usdt=total_exposure_usdt,
        total_margin_used_usdt=total_margin_used_usdt,
        total_unrealized_pnl_usdt=total_unrealized_pnl_usdt,
        connection_status=status,
        last_update_at=last_update_at,
    )


__all__ = ["AccountSummary", "ConnectionStatus", "PositionView", "build_account_summary"]
