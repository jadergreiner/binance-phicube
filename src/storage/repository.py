"""
Repositório MongoDB — persistência de trades, sinais e logs de auditoria.

Coleções:
    trades   — operações executadas (abertas e encerradas)
    signals  — todos os sinais detectados (executados ou não)
    audit    — log imutável de todas as ações do sistema
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel

from src.monitoring.logger import get_logger
from src.trading.order_manager import Trade, TradeStatus

logger = get_logger(__name__)

_TRADES_COLLECTION = "trades"
_SIGNALS_COLLECTION = "signals"
_AUDIT_COLLECTION = "audit"


class MongoRepository:
    """Async MongoDB repository using motor."""

    def __init__(self, uri: str, database: str) -> None:
        self._client: AsyncIOMotorClient = AsyncIOMotorClient(uri)
        self._db: AsyncIOMotorDatabase = self._client[database]

    @property
    def database(self) -> AsyncIOMotorDatabase:
        """Expõe o banco para componentes auxiliares de persistência."""
        return self._db

    async def setup_indexes(self) -> None:
        """Create indexes on first startup. Safe to call on every start."""
        trades = self._db[_TRADES_COLLECTION]
        await trades.create_indexes(
            [
                IndexModel([("symbol", ASCENDING), ("status", ASCENDING)]),
                IndexModel([("opened_at", DESCENDING)]),
                IndexModel([("entry_order_id", ASCENDING)], unique=True),
            ]
        )

        signals = self._db[_SIGNALS_COLLECTION]
        await signals.create_indexes(
            [
                IndexModel([("symbol", ASCENDING), ("timeframe", ASCENDING)]),
                IndexModel([("detected_at", DESCENDING)]),
            ]
        )

        audit = self._db[_AUDIT_COLLECTION]
        await audit.create_indexes(
            [
                IndexModel([("ts", DESCENDING)]),
                IndexModel([("event", ASCENDING)]),
            ]
        )

        logger.info("mongodb_indexes_ready")

    async def close(self) -> None:
        self._client.close()

    # ─── Trades ───────────────────────────────────────────────────────────────

    async def save_trade(self, trade: Trade) -> str:
        result = await self._db[_TRADES_COLLECTION].insert_one(trade.to_dict())
        doc_id = str(result.inserted_id)
        logger.info("trade_saved", symbol=trade.symbol, doc_id=doc_id)
        return doc_id

    async def update_trade_status(
        self,
        entry_order_id: str,
        status: TradeStatus,
        pnl: float | None = None,
    ) -> None:
        update: dict[str, Any] = {
            "$set": {
                "status": status.value,
                "closed_at": datetime.now(UTC),
            }
        }
        if pnl is not None:
            update["$set"]["pnl"] = pnl

        await self._db[_TRADES_COLLECTION].update_one(
            {"entry_order_id": entry_order_id},
            update,
        )
        logger.info("trade_status_updated", entry_order_id=entry_order_id, status=status.value)

    async def get_open_trades(self) -> list[dict]:
        cursor = self._db[_TRADES_COLLECTION].find({"status": TradeStatus.OPEN.value})
        return await cursor.to_list(length=None)

    async def get_open_trades_for_symbol(self, symbol: str) -> list[dict]:
        cursor = self._db[_TRADES_COLLECTION].find(
            {"symbol": symbol, "status": TradeStatus.OPEN.value}
        )
        return await cursor.to_list(length=None)

    async def count_open_trades(self) -> int:
        return await self._db[_TRADES_COLLECTION].count_documents(
            {"status": TradeStatus.OPEN.value}
        )

    # ─── Signals ──────────────────────────────────────────────────────────────

    async def save_signal(self, signal_dict: dict) -> str:
        result = await self._db[_SIGNALS_COLLECTION].insert_one(signal_dict)
        return str(result.inserted_id)

    # ─── Audit log ────────────────────────────────────────────────────────────

    async def audit(self, event: str, data: dict[str, Any]) -> None:
        """Append an immutable audit entry."""
        doc = {
            "ts": datetime.now(UTC),
            "event": event,
            **data,
        }
        await self._db[_AUDIT_COLLECTION].insert_one(doc)
