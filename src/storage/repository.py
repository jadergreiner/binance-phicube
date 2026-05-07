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
from pymongo.errors import DuplicateKeyError

from src.monitoring.logger import get_logger
from src.trading.order_manager import Trade, TradeStatus

logger = get_logger(__name__)

_TRADES_COLLECTION = "trades"
_SIGNALS_COLLECTION = "signals"
_AUDIT_COLLECTION = "audit"
_ONBOARDING_COLLECTION = "symbol_onboarding"


def _calc_metrics(trades: list[dict]) -> dict[str, float | int]:
    """Calcula as 6 métricas RF-11 sobre uma lista de trades fechados."""
    if not trades:
        return {
            "total_trades": 0,
            "win_rate_pct": 0.0,
            "total_pnl_usdt": 0.0,
            "avg_rrr": 0.0,
            "max_drawdown_usdt": 0.0,
            "profit_factor": 0.0,
        }

    pnls = [t["pnl_usdt"] for t in trades if t.get("pnl_usdt") is not None]
    total = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    total_pnl = sum(pnls)
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))

    rrrs = []
    for t in trades:
        risk = t.get("risk_amount") or 0.0
        pnl = t.get("pnl_usdt")
        if pnl is not None and risk > 0:
            rrrs.append(pnl / risk)
    avg_rrr = sum(rrrs) / len(rrrs) if rrrs else 0.0

    peak = 0.0
    cumulative = 0.0
    max_drawdown = 0.0
    sorted_trades = sorted(trades, key=lambda t: t.get("closed_at") or datetime.min)
    for t in sorted_trades:
        pnl = t.get("pnl_usdt") or 0.0
        cumulative += pnl
        if cumulative > peak:
            peak = cumulative
        drawdown = peak - cumulative
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

    return {
        "total_trades": total,
        "win_rate_pct": round(wins / total * 100, 2),
        "total_pnl_usdt": round(total_pnl, 4),
        "avg_rrr": round(avg_rrr, 4),
        "max_drawdown_usdt": round(-max_drawdown, 4),
        "profit_factor": round(profit_factor, 4),
    }


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
                IndexModel([("status", ASCENDING), ("closed_at", DESCENDING)]),
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
                # TTL parcial: expira heartbeats após 24 h sem afetar outros documentos (INV-017-04)
                IndexModel(
                    [("ts", ASCENDING)],
                    expireAfterSeconds=86400,
                    partialFilterExpression={"event": "heartbeat"},
                    name="heartbeat_ttl",
                ),
            ]
        )

        onboarding = self._db[_ONBOARDING_COLLECTION]
        await onboarding.create_indexes(
            [
                IndexModel([("symbol", ASCENDING)], unique=True),
                IndexModel([("status", ASCENDING), ("created_at", DESCENDING)]),
            ]
        )

        logger.info("mongodb_indexes_ready")

    async def close(self) -> None:
        self._client.close()

    # ─── Trades ───────────────────────────────────────────────────────────────

    async def save_trade(self, trade: Trade) -> str | None:
        try:
            result = await self._db[_TRADES_COLLECTION].insert_one(trade.to_dict())
            doc_id = str(result.inserted_id)
            logger.info("trade_saved", symbol=trade.symbol, doc_id=doc_id)
            return doc_id
        except DuplicateKeyError:
            logger.warning("trade_duplicado_ignorado", entry_order_id=trade.entry_order_id)
            return None

    async def update_trade_status(
        self,
        entry_order_id: str,
        status: TradeStatus,
        pnl: float | None = None,
        exit_price: float | None = None,
        pnl_usdt: float | None = None,
        close_reason: str | None = None,
    ) -> None:
        update: dict[str, Any] = {
            "$set": {
                "status": status.value,
                "closed_at": datetime.now(UTC),
            }
        }
        if pnl is not None:
            update["$set"]["pnl"] = pnl
        if exit_price is not None:
            update["$set"]["exit_price"] = exit_price
        if pnl_usdt is not None:
            update["$set"]["pnl_usdt"] = pnl_usdt
        if close_reason is not None:
            update["$set"]["close_reason"] = close_reason

        await self._db[_TRADES_COLLECTION].update_one(
            {"entry_order_id": entry_order_id},
            update,
        )
        logger.info("trade_status_updated", entry_order_id=entry_order_id, status=status.value)

    async def update_sl_orphan_first_detected(
        self,
        entry_order_id: str,
        first_detected_at: datetime,
    ) -> None:
        """Persiste sl_missing_first_detected_at no primeiro alerta de SL órfão (RF-003)."""
        await self._db[_TRADES_COLLECTION].update_one(
            {"entry_order_id": entry_order_id},
            {"$set": {"sl_missing_first_detected_at": first_detected_at}},
        )
        logger.info("sl_orphan_first_detected_saved", entry_order_id=entry_order_id)

    async def update_sl_orphan_metrics(
        self,
        entry_order_id: str,
        sl_restored_at: datetime,
        response_time_seconds: int,
        notification_count: int,
    ) -> None:
        """Persiste métricas de resolução de SL órfão (RF-004, RF-005)."""
        await self._db[_TRADES_COLLECTION].update_one(
            {"entry_order_id": entry_order_id},
            {
                "$set": {
                    "sl_restored_at": sl_restored_at,
                    "sl_missing_response_time_seconds": response_time_seconds,
                    "sl_missing_notification_count": notification_count,
                }
            },
        )
        logger.info(
            "sl_orphan_metrics_saved",
            entry_order_id=entry_order_id,
            response_time_seconds=response_time_seconds,
            notification_count=notification_count,
        )

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

    async def get_performance_metrics(self) -> dict[str, float | int]:
        """Calcula métricas de performance agregadas sobre trades fechados (RF-11)."""
        trades = await self._fetch_closed_trades()
        return _calc_metrics(trades)

    async def get_performance_by_symbol(self) -> dict[str, dict]:
        """Retorna métricas RF-11 agrupadas por símbolo (SPEC_009)."""
        trades = await self._fetch_closed_trades(include_group_fields=True)
        groups: dict[str, list] = {}
        for t in trades:
            groups.setdefault(t.get("symbol", "unknown"), []).append(t)
        return {sym: _calc_metrics(ts) for sym, ts in groups.items()}

    async def get_performance_by_timeframe(self) -> dict[str, dict]:
        """Retorna métricas RF-11 agrupadas por timeframe (SPEC_009)."""
        trades = await self._fetch_closed_trades(include_group_fields=True)
        groups: dict[str, list] = {}
        for t in trades:
            groups.setdefault(t.get("timeframe", "unknown"), []).append(t)
        return {tf: _calc_metrics(ts) for tf, ts in groups.items()}

    async def get_trade_history(self, limit: int = 50) -> list[dict]:
        """Retorna os últimos trades fechados ordenados por closed_at DESC."""
        pipeline = [
            {
                "$match": {
                    "status": {
                        "$in": [
                            TradeStatus.CLOSED_TP.value,
                            TradeStatus.CLOSED_SL.value,
                            TradeStatus.CLOSED_MANUAL.value,
                        ]
                    }
                }
            },
            {"$sort": {"closed_at": -1}},
            {"$limit": limit},
            {
                "$project": {
                    "_id": 0,
                    "symbol": 1,
                    "timeframe": 1,
                    "direction": 1,
                    "entry_price": 1,
                    "exit_price": 1,
                    "stop_loss": 1,
                    "take_profit": 1,
                    "pnl_usdt": 1,
                    "status": 1,
                    "opened_at": 1,
                    "closed_at": 1,
                }
            },
        ]
        cursor = self._db[_TRADES_COLLECTION].aggregate(pipeline)
        return await cursor.to_list(length=limit)

    async def get_open_trade_sl_tp(self) -> dict[str, dict[str, float | None]]:
        """Retorna {symbol: {sl_price, tp_price}} para trades OPEN."""
        cursor = self._db[_TRADES_COLLECTION].find(
            {"status": TradeStatus.OPEN.value},
            {"_id": 0, "symbol": 1, "stop_loss": 1, "take_profit": 1},
        )
        trades = await cursor.to_list(length=None)
        return {
            trade["symbol"]: {
                "sl_price": trade.get("stop_loss"),
                "tp_price": trade.get("take_profit"),
            }
            for trade in trades
            if trade.get("symbol")
        }

    async def get_last_heartbeat_at(self) -> datetime | None:
        """Retorna o timestamp do último heartbeat gravado pelo processo bot.

        Consulta collection audit filtrando event == "heartbeat", ordenando por ts DESC.
        Retorna None se nenhum heartbeat encontrado.
        """
        doc = await self._db[_AUDIT_COLLECTION].find_one(
            {"event": "heartbeat"},
            sort=[("ts", DESCENDING)],
        )
        if doc is None:
            return None
        ts = doc.get("ts")
        if ts is None:
            return None
        return ts if ts.tzinfo else ts.replace(tzinfo=UTC)

    async def get_last_bot_activity_at(self) -> datetime | None:
        """Retorna o timestamp da atividade mais recente entre signals e audit."""
        signal_doc = await self._db[_SIGNALS_COLLECTION].find_one(
            {},
            projection={"_id": 1},
            sort=[("_id", DESCENDING)],
        )
        audit_doc = await self._db[_AUDIT_COLLECTION].find_one(
            {},
            projection={"_id": 1},
            sort=[("_id", DESCENDING)],
        )
        candidates: list[datetime] = []
        for doc in (signal_doc, audit_doc):
            if doc is None:
                continue
            object_id = doc.get("_id")
            generation_time = getattr(object_id, "generation_time", None)
            if generation_time is not None:
                candidates.append(generation_time.astimezone(UTC))

        if not candidates:
            return None

        return max(candidates)

    async def _fetch_closed_trades(self, *, include_group_fields: bool = False) -> list[dict]:
        closed_statuses = [
            TradeStatus.CLOSED_TP.value,
            TradeStatus.CLOSED_SL.value,
            TradeStatus.CLOSED_MANUAL.value,
        ]
        projection: dict[str, int] = {"pnl_usdt": 1, "risk_amount": 1, "closed_at": 1, "_id": 0}
        if include_group_fields:
            projection["symbol"] = 1
            projection["timeframe"] = 1
        cursor = self._db[_TRADES_COLLECTION].find(
            {"status": {"$in": closed_statuses}, "pnl_usdt": {"$ne": None}},
            projection,
        )
        return await cursor.to_list(length=None)

    # ─── Onboarding ───────────────────────────────────────────────────────────

    async def create_onboarding_session(self, doc: dict[str, Any]) -> None:
        await self._db[_ONBOARDING_COLLECTION].insert_one(doc)

    async def get_onboarding_session(self, symbol: str) -> dict[str, Any] | None:
        return await self._db[_ONBOARDING_COLLECTION].find_one(
            {"symbol": symbol}, {"_id": 0}
        )

    async def list_onboarding_sessions(self) -> list[dict[str, Any]]:
        cursor = self._db[_ONBOARDING_COLLECTION].find({}, {"_id": 0}).sort(
            "created_at", DESCENDING
        )
        return await cursor.to_list(length=None)

    async def update_onboarding_session(self, symbol: str, update: dict[str, Any]) -> None:
        update["updated_at"] = datetime.now(UTC)
        await self._db[_ONBOARDING_COLLECTION].update_one(
            {"symbol": symbol}, {"$set": update}
        )

    async def delete_onboarding_session(self, symbol: str) -> bool:
        result = await self._db[_ONBOARDING_COLLECTION].delete_one({"symbol": symbol})
        return result.deleted_count > 0

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
