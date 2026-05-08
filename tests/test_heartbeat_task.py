"""
Testes de conformidade SPEC_017 — HeartbeatTask.

Cobre:
- TEST_017_01: _beat() chama repo.audit com event "heartbeat" e campos corretos
- TEST_017_02: falha ao gravar não propaga exceção (INV-017-01)
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.main import HeartbeatTask


def _make_task(monitor_count: int = 2) -> HeartbeatTask:
    repo = MagicMock()
    repo.audit = AsyncMock()
    return HeartbeatTask(repo=repo, monitor_count=monitor_count)


@pytest.mark.asyncio
async def test_beat_chama_audit_com_event_heartbeat() -> None:
    """TEST_017_01: _beat() grava na collection audit com event 'heartbeat'."""
    task = _make_task(monitor_count=3)

    await task._beat()

    task._repo.audit.assert_awaited_once()
    event_arg, data_arg = task._repo.audit.call_args[0]
    assert event_arg == "heartbeat"
    assert "process_uptime_seconds" in data_arg
    assert data_arg["monitor_count"] == 3
    assert data_arg["metadata"]["source"] == "HeartbeatTask"


@pytest.mark.asyncio
async def test_beat_process_uptime_seconds_e_inteiro() -> None:
    """process_uptime_seconds deve ser int >= 0."""
    task = _make_task()
    await task._beat()

    _, data_arg = task._repo.audit.call_args[0]
    uptime = data_arg["process_uptime_seconds"]
    assert isinstance(uptime, int)
    assert uptime >= 0


@pytest.mark.asyncio
async def test_run_nao_propaga_excecao_de_audit() -> None:
    """TEST_017_02: falha ao gravar heartbeat não interrompe o loop (INV-017-01)."""
    repo = MagicMock()
    repo.audit = AsyncMock(side_effect=RuntimeError("mongo down"))
    task = HeartbeatTask(repo=repo, monitor_count=1)
    # Força intervalo 0 para que beats ocorram rapidamente no teste
    task.__class__ = type("HeartbeatTaskFast", (HeartbeatTask,), {"INTERVAL_SECONDS": 0})

    t = asyncio.create_task(task.run())
    await asyncio.sleep(0.05)
    t.cancel()
    try:
        await t
    except asyncio.CancelledError:
        pass

    # Loop rodou sem re-levantar RuntimeError e audit foi chamado
    assert repo.audit.await_count >= 1


@pytest.mark.asyncio
async def test_run_encerra_limpo_em_cancelled_error() -> None:
    """HeartbeatTask.run() encerra sem exceção quando cancelada."""
    task = _make_task()

    async def _run_and_cancel():
        t = asyncio.create_task(task.run())
        await asyncio.sleep(0)
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass

    await _run_and_cancel()
