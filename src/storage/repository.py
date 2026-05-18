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

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.errors import DuplicateKeyError

from src.common.metrics import compute_metrics
from src.monitoring.logger import get_logger
from src.trading.order_manager import Trade, TradeStatus

logger = get_logger(__name__)

_TRADES_COLLECTION = "trades"
_SIGNALS_COLLECTION = "signals"
_AUDIT_COLLECTION = "audit"
_CUSTOMERS_COLLECTION = "customers"
_ONBOARDING_COLLECTION = "symbol_onboarding"
_BACKTEST_JOBS_COLLECTION = "onboarding_backtest_jobs"
_AUDIT_RETENTION_EVENTS = [
    "signal_detected",
    "trade_opened",
    "trade_closed_tp",
    "trade_closed_sl",
    "trade_closed_manual",
    "sl_missing_detected",
    "sl_missing_renotified",
    "sl_missing_cleared",
]
_CLOSED_TRADE_STATUSES = [
    TradeStatus.CLOSED_TP.value,
    TradeStatus.CLOSED_SL.value,
    TradeStatus.CLOSED_MANUAL.value,
]
_ENTRY_PRICE_BOUNDS_BY_SYMBOL: dict[str, tuple[float, float]] = {
    "BTCUSDT": (1000.0, 200000.0),
}


def _is_entry_price_in_range(symbol: str | None, entry_price: float | None) -> bool:
    if symbol is None or entry_price is None:
        return False
    bounds = _ENTRY_PRICE_BOUNDS_BY_SYMBOL.get(symbol.upper())
    if bounds is None:
        return entry_price > 0.0
    min_price, max_price = bounds
    return min_price <= entry_price <= max_price


def _closed_trades_query(*, include_period: dict[str, Any] | None = None) -> dict[str, Any]:
    """Filtro canônico de trades fechados válidos para métricas e histórico.

    Documentos marcados com `excluded_from_metrics=true` são ignorados.
    """
    query: dict[str, Any] = {
        "status": {"$in": _CLOSED_TRADE_STATUSES},
        "pnl_usdt": {"$ne": None},
        "excluded_from_metrics": {"$ne": True},
    }
    if include_period:
        query.update(include_period)
    return query


def _calc_metrics(trades: list[dict]) -> dict[str, float | int]:
    """Calcula as 6 métricas RF-11 sobre uma lista de trades fechados."""
    sorted_trades = sorted(trades, key=lambda t: t.get("closed_at") or datetime.min)
    pnls = [float(t["pnl_usdt"]) for t in sorted_trades if t.get("pnl_usdt") is not None]
    rrrs = []
    for t in sorted_trades:
        risk = t.get("risk_amount") or 0.0
        pnl = t.get("pnl_usdt")
        if pnl is not None and risk > 0:
            rrrs.append(float(pnl) / float(risk))
    return compute_metrics(pnls, rrrs).to_dict()


class MongoRepository:
    """Async MongoDB repository using motor."""

    def __init__(
        self,
        uri: str,
        database: str,
        trade_history_retention_days: int = 90,
    ) -> None:
        self._client: AsyncIOMotorClient = AsyncIOMotorClient(uri)
        self._db: AsyncIOMotorDatabase = self._client[database]
        self._trade_history_retention_days = trade_history_retention_days

    @property
    def database(self) -> AsyncIOMotorDatabase:
        """Expõe o banco para componentes auxiliares de persistência."""
        return self._db

    async def setup_indexes(self) -> None:
        """Create indexes on first startup. Safe to call on every start."""
        retention_seconds = self._trade_history_retention_days * 86400
        closed_statuses = [
            TradeStatus.CLOSED_TP.value,
            TradeStatus.CLOSED_SL.value,
            TradeStatus.CLOSED_MANUAL.value,
            TradeStatus.FAILED.value,
        ]

        trades = self._db[_TRADES_COLLECTION]
        await trades.create_indexes(
            [
                IndexModel([("symbol", ASCENDING), ("status", ASCENDING)]),
                IndexModel([("status", ASCENDING), ("closed_at", DESCENDING)]),
                IndexModel([("opened_at", DESCENDING)]),
                IndexModel([("entry_order_id", ASCENDING)], unique=True),
                # Retenção operacional mínima de histórico de trade (PRD): 90 dias.
                IndexModel(
                    [("closed_at", ASCENDING)],
                    expireAfterSeconds=retention_seconds,
                    partialFilterExpression={"status": {"$in": closed_statuses}},
                    name="trades_closed_retention_ttl",
                ),
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
                # Retenção operacional mínima para trilha de auditoria não-heartbeat.
                IndexModel(
                    [("ts", ASCENDING)],
                    expireAfterSeconds=retention_seconds,
                    partialFilterExpression={"event": {"$in": _AUDIT_RETENTION_EVENTS}},
                    name="audit_retention_ttl",
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

        backtest_jobs = self._db[_BACKTEST_JOBS_COLLECTION]
        await backtest_jobs.create_indexes(
            [
                IndexModel([("job_id", ASCENDING)], unique=True),
                IndexModel([("status", ASCENDING), ("created_at", DESCENDING)]),
                IndexModel([("idempotency_key", ASCENDING), ("status", ASCENDING)]),
                IndexModel(
                    [("completed_at", ASCENDING)],
                    expireAfterSeconds=15 * 86400,
                    partialFilterExpression={
                        "status": {"$in": ["succeeded", "failed", "canceled"]},
                    },
                    name="onboarding_backtest_jobs_retention_ttl",
                ),
            ]
        )

        customers = self._db[_CUSTOMERS_COLLECTION]
        await customers.create_indexes(
            [
                IndexModel([("id", ASCENDING)], unique=True),
                IndexModel([("status", ASCENDING), ("created_at", DESCENDING)]),
                IndexModel([("name", ASCENDING)]),
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
        if status.value in _CLOSED_TRADE_STATUSES:
            trade = await self._db[_TRADES_COLLECTION].find_one(
                {"entry_order_id": entry_order_id},
                {"_id": 0, "symbol": 1, "entry_price": 1},
            )
            symbol = trade.get("symbol") if trade else None
            entry_price = trade.get("entry_price") if trade else None
            if not _is_entry_price_in_range(symbol, entry_price):
                bounds = _ENTRY_PRICE_BOUNDS_BY_SYMBOL.get((symbol or "").upper())
                await self.audit(
                    "trade_close_blocked_invalid_entry_price",
                    {
                        "entry_order_id": entry_order_id,
                        "symbol": symbol,
                        "status_requested": status.value,
                        "entry_price": entry_price,
                        "allowed_range": bounds,
                    },
                )
                logger.warning(
                    "trade_close_blocked_invalid_entry_price",
                    entry_order_id=entry_order_id,
                    symbol=symbol,
                    status_requested=status.value,
                    entry_price=entry_price,
                    allowed_range=bounds,
                )
                return

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
            {"$match": _closed_trades_query()},
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
                    "close_reason": 1,
                    "is_estimated": 1,
                    "opened_at": 1,
                    "closed_at": 1,
                }
            },
        ]
        cursor = self._db[_TRADES_COLLECTION].aggregate(pipeline)
        return await cursor.to_list(length=limit)

    async def get_intraday_realized_pnl_usdt(self, now: datetime | None = None) -> float:
        """Retorna PnL realizado intraday em USDT para o dia UTC corrente."""
        ref = now.astimezone(UTC) if now else datetime.now(UTC)
        start_of_day = ref.replace(hour=0, minute=0, second=0, microsecond=0)
        cursor = self._db[_TRADES_COLLECTION].find(
            _closed_trades_query(include_period={"closed_at": {"$gte": start_of_day}}),
            {"_id": 0, "pnl_usdt": 1},
        )
        rows = await cursor.to_list(length=None)
        return round(sum(float(row.get("pnl_usdt") or 0.0) for row in rows), 4)

    async def get_trade_by_entry_order_id(self, entry_order_id: str) -> dict | None:
        """Retorna um trade pelo entry_order_id."""
        return await self._db[_TRADES_COLLECTION].find_one(
            {"entry_order_id": entry_order_id}, {"_id": 0}
        )

    async def update_trade_orders(
        self,
        entry_order_id: str,
        *,
        sl_order_id: str | None = None,
        tp_order_id: str | None = None,
    ) -> None:
        """Atualiza IDs de SL/TP de um trade (reconciliação com a exchange)."""
        update: dict[str, Any] = {}
        if sl_order_id is not None:
            update["sl_order_id"] = sl_order_id
        if tp_order_id is not None:
            update["tp_order_id"] = tp_order_id
        if not update:
            return
        await self._db[_TRADES_COLLECTION].update_one(
            {"entry_order_id": entry_order_id},
            {"$set": update},
        )
        logger.info(
            "trade_orders_updated",
            entry_order_id=entry_order_id,
            sl_order_id=sl_order_id,
            tp_order_id=tp_order_id,
        )

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
        projection: dict[str, int] = {"pnl_usdt": 1, "risk_amount": 1, "closed_at": 1, "_id": 0}
        if include_group_fields:
            projection["symbol"] = 1
            projection["timeframe"] = 1
        cursor = self._db[_TRADES_COLLECTION].find(
            _closed_trades_query(),
            projection,
        )
        return await cursor.to_list(length=None)

    async def get_closed_trades_in_period(
        self,
        *,
        start: datetime,
        end: datetime,
        symbol: str | None = None,
        timeframe: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retorna trades fechados no período para análises de assertividade."""
        query: dict[str, Any] = _closed_trades_query(
            include_period={"closed_at": {"$gte": start, "$lte": end}}
        )
        if symbol:
            query["symbol"] = symbol
        if timeframe:
            query["timeframe"] = timeframe
        projection = {
            "_id": 0,
            "symbol": 1,
            "timeframe": 1,
            "closed_at": 1,
            "pnl_usdt": 1,
            "risk_amount": 1,
        }
        cursor = self._db[_TRADES_COLLECTION].find(query, projection)
        return await cursor.to_list(length=None)

    async def get_signals_in_period(
        self,
        *,
        start: datetime,
        end: datetime,
        symbol: str | None = None,
        timeframe: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retorna sinais detectados no período para análise de conversão."""
        query: dict[str, Any] = {
            "detected_at": {"$gte": start, "$lte": end},
        }
        if symbol:
            query["symbol"] = symbol
        if timeframe:
            query["timeframe"] = timeframe
        projection = {
            "_id": 0,
            "symbol": 1,
            "timeframe": 1,
            "detected_at": 1,
            "execution_status": 1,
        }
        cursor = self._db[_SIGNALS_COLLECTION].find(query, projection)
        return await cursor.to_list(length=None)

    # ─── MCP-PoS Customers ──────────────────────────────────────────────────

    async def list_customers(self, limit: int = 50, skip: int = 0) -> list[dict[str, Any]]:
        cursor = (
            self._db[_CUSTOMERS_COLLECTION]
            .find({}, {"_id": 0})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def get_customer(self, customer_id: str) -> dict[str, Any] | None:
        return await self._db[_CUSTOMERS_COLLECTION].find_one({"id": customer_id}, {"_id": 0})

    async def create_customer(self, customer: dict[str, Any]) -> str | None:
        result = await self._db[_CUSTOMERS_COLLECTION].insert_one(customer)
        return str(result.inserted_id)

    async def update_customer(self, customer_id: str, update: dict[str, Any]) -> bool:
        update["updated_at"] = datetime.now(UTC)
        result = await self._db[_CUSTOMERS_COLLECTION].update_one(
            {"id": customer_id}, {"$set": update}
        )
        return result.matched_count > 0

    async def delete_customer(self, customer_id: str) -> bool:
        result = await self._db[_CUSTOMERS_COLLECTION].delete_one({"id": customer_id})
        return result.deleted_count > 0

    async def count_customers(self) -> int:
        return await self._db[_CUSTOMERS_COLLECTION].count_documents({})

    # ─── Onboarding ───────────────────────────────────────────────────────────

    async def create_onboarding_session(self, doc: dict[str, Any]) -> None:
        await self._db[_ONBOARDING_COLLECTION].insert_one(doc)

    async def get_onboarding_session(self, symbol: str) -> dict[str, Any] | None:
        return await self._db[_ONBOARDING_COLLECTION].find_one({"symbol": symbol}, {"_id": 0})

    async def list_onboarding_sessions(self) -> list[dict[str, Any]]:
        cursor = (
            self._db[_ONBOARDING_COLLECTION].find({}, {"_id": 0}).sort("created_at", DESCENDING)
        )
        return await cursor.to_list(length=None)

    async def update_onboarding_session(self, symbol: str, update: dict[str, Any]) -> None:
        update["updated_at"] = datetime.now(UTC)
        await self._db[_ONBOARDING_COLLECTION].update_one({"symbol": symbol}, {"$set": update})

    async def delete_onboarding_session(self, symbol: str) -> bool:
        result = await self._db[_ONBOARDING_COLLECTION].delete_one({"symbol": symbol})
        return result.deleted_count > 0

    # ─── Onboarding Backtest Jobs ────────────────────────────────────────────

    async def create_backtest_job(self, doc: dict[str, Any]) -> None:
        await self._db[_BACKTEST_JOBS_COLLECTION].insert_one(doc)

    async def get_backtest_job(self, job_id: str) -> dict[str, Any] | None:
        return await self._db[_BACKTEST_JOBS_COLLECTION].find_one({"job_id": job_id}, {"_id": 0})

    async def get_active_backtest_job_by_key(self, idempotency_key: str) -> dict[str, Any] | None:
        return await self._db[_BACKTEST_JOBS_COLLECTION].find_one(
            {
                "idempotency_key": idempotency_key,
                "status": {"$in": ["queued", "running"]},
            },
            {"_id": 0},
            sort=[("created_at", DESCENDING)],
        )

    async def update_backtest_job(self, job_id: str, update: dict[str, Any]) -> bool:
        payload = dict(update)
        payload["updated_at"] = datetime.now(UTC)
        result = await self._db[_BACKTEST_JOBS_COLLECTION].update_one(
            {"job_id": job_id},
            {"$set": payload},
        )
        return result.matched_count > 0

    # ─── Signals ──────────────────────────────────────────────────────────────

    async def save_signal(self, signal_dict: dict) -> str:
        result = await self._db[_SIGNALS_COLLECTION].insert_one(signal_dict)
        return str(result.inserted_id)

    async def update_signal_execution_outcome(
        self,
        signal_id: str,
        *,
        execution_status: str,
        execution_reason: str | None = None,
        execution_details: dict[str, Any] | None = None,
        trade_id: str | None = None,
        outcome_at: datetime | None = None,
    ) -> bool:
        try:
            object_id = ObjectId(signal_id)
        except (InvalidId, TypeError):
            logger.warning("signal_outcome_update_invalid_id", signal_id=signal_id)
            return False

        update: dict[str, Any] = {
            "execution_status": execution_status,
            "outcome_at": outcome_at or datetime.now(UTC),
        }
        if execution_reason is not None:
            update["execution_reason"] = execution_reason
        if execution_details is not None:
            update["execution_details"] = execution_details
        if trade_id is not None:
            update["trade_id"] = trade_id

        result = await self._db[_SIGNALS_COLLECTION].update_one(
            {"_id": object_id},
            {"$set": update},
        )
        return result.matched_count > 0

    async def get_signal_history(self, limit: int = 50) -> list[dict]:
        pipeline = [
            {"$sort": {"detected_at": -1}},
            {"$limit": limit},
            {
                "$project": {
                    "_id": 0,
                    "symbol": 1,
                    "timeframe": 1,
                    "direction": 1,
                    "entry_price": 1,
                    "stop_loss": 1,
                    "take_profit": 1,
                    "risk_reward_ratio": 1,
                    "detected_at": 1,
                    "execution_status": 1,
                    "execution_reason": 1,
                    "execution_details": 1,
                    "trade_id": 1,
                    "outcome_at": 1,
                    "backtest_outcome": 1,
                    "backtest_outcome_price": 1,
                    "backtest_outcome_at": 1,
                    "backtest_pnl_pct": 1,
                    "backtest_candles_checked": 1,
                }
            },
        ]
        cursor = self._db[_SIGNALS_COLLECTION].aggregate(pipeline)
        return await cursor.to_list(length=limit)

    async def get_advisory_signals(self, limit: int = 200) -> list[dict]:
        """Retorna sinais em modo advisory ainda não classificados por backtest."""
        pipeline = [
            {
                "$match": {
                    "execution_status": {"$regex": "advisory|REJECTED", "$options": "i"},
                    "backtest_outcome": {"$exists": False},
                    "entry_price": {"$exists": True},
                    "stop_loss": {"$exists": True},
                    "take_profit": {"$exists": True},
                }
            },
            {"$sort": {"detected_at": -1}},
            {"$limit": limit},
            {
                "$project": {
                    "_id": {"$toString": "$_id"},
                    "symbol": 1,
                    "timeframe": 1,
                    "direction": 1,
                    "entry_price": 1,
                    "stop_loss": 1,
                    "take_profit": 1,
                    "detected_at": 1,
                    "execution_status": 1,
                }
            },
        ]
        cursor = self._db[_SIGNALS_COLLECTION].aggregate(pipeline)
        return await cursor.to_list(length=limit)

    async def set_signal_backtest_outcome(
        self,
        signal_id: str,
        *,
        outcome: str,
        outcome_price: float | None = None,
        outcome_at: datetime | None = None,
        candles_checked: int = 0,
    ) -> bool:
        """Persiste resultado do backtest no sinal (TP_HIT, SL_HIT, OPEN)."""
        try:
            object_id = ObjectId(signal_id)
        except (InvalidId, TypeError):
            return False
        update = {
            "backtest_outcome": outcome,
            "backtest_at": datetime.now(UTC),
            "backtest_candles_checked": candles_checked,
        }
        if outcome_price is not None:
            update["backtest_outcome_price"] = outcome_price
        if outcome_at is not None:
            update["backtest_outcome_at"] = outcome_at
        result = await self._db[_SIGNALS_COLLECTION].update_one(
            {"_id": object_id}, {"$set": update}
        )
        return result.matched_count > 0

    async def get_latest_signal_diagnostics(self, limit: int = 10) -> list[dict]:
        pipeline = [
            {"$match": {"event": "signal_evaluated"}},
            {"$sort": {"ts": -1}},
            {
                "$group": {
                    "_id": {"symbol": "$symbol", "timeframe": "$timeframe"},
                    "doc": {"$first": "$$ROOT"},
                }
            },
            {"$replaceRoot": {"newRoot": "$doc"}},
            {"$sort": {"ts": -1}},
            {"$limit": limit},
            {
                "$project": {
                    "_id": 0,
                    "symbol": 1,
                    "timeframe": 1,
                    "decision": 1,
                    "signal_generated": 1,
                    "reason": 1,
                    "evaluated_at": 1,
                    "candle_open_time": 1,
                    "long_conditions": 1,
                    "short_conditions": 1,
                    "ts": 1,
                }
            },
        ]
        cursor = self._db[_AUDIT_COLLECTION].aggregate(pipeline)
        return await cursor.to_list(length=limit)

    async def get_signal_generation_diagnosis(
        self,
        symbol: str,
        timeframe: str,
    ) -> dict[str, Any]:
        latest_cycle = await self._db[_AUDIT_COLLECTION].find_one(
            {
                "event": "signal_cycle_diagnostic",
                "symbol": symbol,
                "timeframe": timeframe,
            },
            sort=[("ts", DESCENDING)],
        )
        if latest_cycle is None:
            last_heartbeat = await self._db[_AUDIT_COLLECTION].find_one(
                {"event": "heartbeat"},
                sort=[("ts", DESCENDING)],
            )
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "classification": "PIPELINE_INTERRUPTED",
                "last_evidence_at": None,
                "risk_reason": None,
                "engine_outcome": None,
                "engine_reason": None,
                "reason": None,
                "rule_hits": [],
                "phicube_mode": "shadow",
                "explicacao_humana": None,
                "risk_outcome": None,
                "ml_enabled": False,
                "ml_shadow_mode": False,
                "ml_score": None,
                "ml_decision": None,
                "ml_reason": None,
                "ml_model_version": None,
                "details": {
                    "reason": "no_signal_cycle_diagnostic_event_found",
                    "last_heartbeat_at": last_heartbeat.get("ts") if last_heartbeat else None,
                    "market_state": None,
                },
            }

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "classification": latest_cycle.get("final_status"),
            "last_evidence_at": latest_cycle.get("ts"),
            "risk_reason": latest_cycle.get("risk_reason"),
            "engine_outcome": latest_cycle.get("engine_outcome"),
            "engine_reason": latest_cycle.get("engine_reason"),
            "reason": latest_cycle.get("reason"),
            "rule_hits": latest_cycle.get("rule_hits") or [],
            "phicube_mode": latest_cycle.get("phicube_mode") or "shadow",
            "explicacao_humana": latest_cycle.get("explicacao_humana"),
            "risk_outcome": latest_cycle.get("risk_outcome"),
            "ml_enabled": bool(latest_cycle.get("ml_enabled", False)),
            "ml_shadow_mode": bool(latest_cycle.get("ml_shadow_mode", False)),
            "ml_score": latest_cycle.get("ml_score"),
            "ml_decision": latest_cycle.get("ml_decision"),
            "ml_reason": latest_cycle.get("ml_reason"),
            "ml_model_version": latest_cycle.get("ml_model_version"),
            "details": {
                "candle_close_time": latest_cycle.get("candle_close_time"),
                "engine_reason": latest_cycle.get("engine_reason"),
                "market_state": latest_cycle.get("market_state"),
                "ml_reason": latest_cycle.get("ml_reason"),
                "technical_indicators": latest_cycle.get("technical_indicators"),
            },
        }

    # ─── Audit log ────────────────────────────────────────────────────────────

    async def audit(self, event: str, data: dict[str, Any]) -> None:
        """Append an immutable audit entry."""
        doc = {
            "ts": datetime.now(UTC),
            "event": event,
            **data,
        }
        await self._db[_AUDIT_COLLECTION].insert_one(doc)
