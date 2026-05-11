"""
Testes de conformidade SPEC_017 — get_last_heartbeat_at() no MongoRepository.

Cobre:
- TEST_017_08: retorna datetime correto quando heartbeat existe
- TEST_017_09: retorna None quando collection vazia ou sem heartbeats
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.storage.repository import MongoRepository


def _make_repo() -> MongoRepository:
    with patch("src.storage.repository.AsyncIOMotorClient"):
        repo = MongoRepository.__new__(MongoRepository)
        repo._db = MagicMock()
        return repo


@pytest.mark.asyncio
async def test_get_last_heartbeat_at_retorna_datetime() -> None:
    """TEST_017_08: collection audit com heartbeat → retorna ts do documento mais recente."""
    repo = _make_repo()
    expected_ts = datetime(2026, 5, 6, 15, 0, 0, tzinfo=UTC)

    repo._db.__getitem__ = MagicMock(return_value=MagicMock())
    audit_col = repo._db["audit"]
    audit_col.find_one = AsyncMock(return_value={"event": "heartbeat", "ts": expected_ts})

    result = await repo.get_last_heartbeat_at()

    assert result == expected_ts
    audit_col.find_one.assert_awaited_once()
    call_kwargs = audit_col.find_one.call_args
    assert call_kwargs[0][0] == {"event": "heartbeat"}


@pytest.mark.asyncio
async def test_get_last_heartbeat_at_retorna_none_sem_heartbeat() -> None:
    """TEST_017_09: collection audit vazia ou sem heartbeats → None."""
    repo = _make_repo()

    repo._db.__getitem__ = MagicMock(return_value=MagicMock())
    audit_col = repo._db["audit"]
    audit_col.find_one = AsyncMock(return_value=None)

    result = await repo.get_last_heartbeat_at()

    assert result is None


@pytest.mark.asyncio
async def test_get_last_heartbeat_at_adiciona_tzinfo_se_naive() -> None:
    """Documento com ts naive (sem tzinfo) recebe UTC automaticamente."""
    repo = _make_repo()
    naive_ts = datetime(2026, 5, 6, 15, 0, 0)

    repo._db.__getitem__ = MagicMock(return_value=MagicMock())
    audit_col = repo._db["audit"]
    audit_col.find_one = AsyncMock(return_value={"event": "heartbeat", "ts": naive_ts})

    result = await repo.get_last_heartbeat_at()

    assert result is not None
    assert result.tzinfo is not None


@pytest.mark.asyncio
async def test_get_last_heartbeat_at_retorna_none_quando_ts_ausente() -> None:
    """Documento de heartbeat sem campo 'ts' → retorna None graciosamente."""
    repo = _make_repo()

    repo._db.__getitem__ = MagicMock(return_value=MagicMock())
    audit_col = repo._db["audit"]
    audit_col.find_one = AsyncMock(return_value={"event": "heartbeat"})

    result = await repo.get_last_heartbeat_at()

    assert result is None
