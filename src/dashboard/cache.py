"""Cache frio do último snapshot válido do painel no MongoDB."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from src.dashboard.models import PositionView
from src.monitoring.logger import get_logger

logger = get_logger(__name__)

_DASHBOARD_SNAPSHOT_COLLECTION = "dashboard_snapshot"
_LATEST_SNAPSHOT_ID = "latest"


class DashboardCache:
    """Persistência auxiliar do último snapshot válido do painel."""

    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self._collection = database[_DASHBOARD_SNAPSHOT_COLLECTION]

    def save_snapshot(self, positions: list[PositionView]) -> None:
        """Agenda a persistência do snapshot sem bloquear o fluxo principal."""
        asyncio.create_task(
            self._persist_snapshot(list(positions)),
            name="dashboard-cache-save-snapshot",
        )

    async def load_snapshot(self) -> list[PositionView] | None:
        """Carrega o último snapshot válido do cache, se existir."""
        document = await self._collection.find_one({"_id": _LATEST_SNAPSHOT_ID})
        if document is None:
            return None

        cached_positions = document.get("positions")
        if cached_positions is None:
            return None

        return [self._deserialize_position(position) for position in cached_positions]

    async def _persist_snapshot(self, positions: list[PositionView]) -> None:
        document = {
            "_id": _LATEST_SNAPSHOT_ID,
            "positions": [self._serialize_position(position) for position in positions],
            "cached_at": datetime.now(UTC),
        }

        try:
            await self._collection.replace_one(
                {"_id": _LATEST_SNAPSHOT_ID},
                document,
                upsert=True,
            )
        except Exception as exc:
            logger.warning(
                "dashboard_snapshot_cache_save_failed",
                error=str(exc),
                positions=len(positions),
            )

    @staticmethod
    def _serialize_position(position: PositionView) -> dict[str, object]:
        return asdict(position)

    @staticmethod
    def _deserialize_position(payload: dict[str, Any]) -> PositionView:
        return PositionView(
            symbol=str(payload.get("symbol", "")),
            side=str(payload.get("side", "")),
            quantity=float(payload.get("quantity", 0.0)),
            leverage=int(payload.get("leverage", 0)),
            entry_price=float(payload.get("entry_price", 0.0)),
            mark_price=float(payload.get("mark_price", 0.0)),
            unrealized_pnl_usdt=float(payload.get("unrealized_pnl_usdt", 0.0)),
            margin_used_usdt=float(payload.get("margin_used_usdt", 0.0)),
            liquidation_price=(
                float(payload["liquidation_price"])
                if payload.get("liquidation_price") is not None
                else None
            ),
            updated_at=DashboardCache._normalize_datetime(payload.get("updated_at")),
        )

    @staticmethod
    def _normalize_datetime(value: object) -> datetime:
        if value is None:
            return datetime.now(UTC)

        if isinstance(value, datetime):
            if value.tzinfo is None or value.utcoffset() is None:
                return value.replace(tzinfo=UTC)
            return value.astimezone(UTC)

        return datetime.fromisoformat(str(value)).astimezone(UTC)


__all__ = ["DashboardCache"]
