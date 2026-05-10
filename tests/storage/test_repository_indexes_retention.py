from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.storage.repository import (
    _AUDIT_COLLECTION,
    _AUDIT_RETENTION_EVENTS,
    _BACKTEST_JOBS_COLLECTION,
    _ONBOARDING_COLLECTION,
    _SIGNALS_COLLECTION,
    _TRADES_COLLECTION,
    MongoRepository,
)


def _make_repo(retention_days: int = 90) -> MongoRepository:
    with patch("motor.motor_asyncio.AsyncIOMotorClient"):
        return MongoRepository(
            "mongodb://localhost/test",
            "test_db",
            trade_history_retention_days=retention_days,
        )


@pytest.mark.asyncio
async def test_setup_indexes_respeita_retencao_minima_90_dias() -> None:
    repo = _make_repo(retention_days=90)

    trades_col = AsyncMock()
    signals_col = AsyncMock()
    audit_col = AsyncMock()
    onboarding_col = AsyncMock()

    backtest_jobs_col = AsyncMock()

    repo._db = MagicMock()
    repo._db.__getitem__.side_effect = lambda name: {
        _TRADES_COLLECTION: trades_col,
        _SIGNALS_COLLECTION: signals_col,
        _AUDIT_COLLECTION: audit_col,
        _ONBOARDING_COLLECTION: onboarding_col,
        _BACKTEST_JOBS_COLLECTION: backtest_jobs_col,
    }[name]

    await repo.setup_indexes()

    trade_indexes = trades_col.create_indexes.call_args.args[0]
    audit_indexes = audit_col.create_indexes.call_args.args[0]

    trade_ttl_idx = next(
        i for i in trade_indexes if i.document.get("name") == "trades_closed_retention_ttl"
    )
    assert trade_ttl_idx.document["expireAfterSeconds"] == 90 * 86400
    assert trade_ttl_idx.document["partialFilterExpression"]["status"]["$in"]

    heartbeat_ttl_idx = next(i for i in audit_indexes if i.document.get("name") == "heartbeat_ttl")
    assert heartbeat_ttl_idx.document["expireAfterSeconds"] == 86400
    assert heartbeat_ttl_idx.document["partialFilterExpression"] == {"event": "heartbeat"}

    audit_ttl_idx = next(
        i for i in audit_indexes if i.document.get("name") == "audit_retention_ttl"
    )
    assert audit_ttl_idx.document["expireAfterSeconds"] == 90 * 86400
    assert audit_ttl_idx.document["partialFilterExpression"] == {
        "event": {"$in": _AUDIT_RETENTION_EVENTS}
    }
