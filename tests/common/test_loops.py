from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.loops import safe_loop


@pytest.mark.asyncio
async def test_safe_loop_repeticao_e_sleep_entre_iteracoes(monkeypatch) -> None:
    chamadas = 0

    async def iteration_fn() -> None:
        nonlocal chamadas
        chamadas += 1
        if chamadas == 3:
            raise asyncio.CancelledError

    sleep_mock = AsyncMock()
    monkeypatch.setattr("src.common.loops.asyncio.sleep", sleep_mock)

    await safe_loop(iteration_fn, interval=1.0, logger=MagicMock())

    assert chamadas == 3
    assert sleep_mock.await_count == 2


@pytest.mark.asyncio
async def test_safe_loop_loga_excecao_e_continua(monkeypatch) -> None:
    chamadas = 0
    logger = MagicMock()

    async def iteration_fn() -> None:
        nonlocal chamadas
        chamadas += 1
        if chamadas == 1:
            raise RuntimeError("boom")
        if chamadas == 3:
            raise asyncio.CancelledError

    sleep_mock = AsyncMock()
    monkeypatch.setattr("src.common.loops.asyncio.sleep", sleep_mock)

    await safe_loop(
        iteration_fn,
        interval=1.0,
        logger=logger,
        loop_name="demo_loop",
    )

    logger.error.assert_called_once()
    args, kwargs = logger.error.call_args
    assert args[0] == "safe_loop_error"
    assert kwargs["loop_name"] == "demo_loop"
    assert kwargs["error_type"] == "RuntimeError"
    assert sleep_mock.await_count == 2


@pytest.mark.asyncio
async def test_safe_loop_passa_erro_para_callback(monkeypatch) -> None:
    chamadas = 0
    erros: list[str] = []
    logger = MagicMock()

    async def iteration_fn() -> None:
        nonlocal chamadas
        chamadas += 1
        if chamadas == 1:
            raise ValueError("erro")
        if chamadas == 2:
            raise asyncio.CancelledError

    def on_error(exc: BaseException) -> None:
        erros.append(type(exc).__name__)

    sleep_mock = AsyncMock()
    monkeypatch.setattr("src.common.loops.asyncio.sleep", sleep_mock)

    await safe_loop(
        iteration_fn,
        interval=1.0,
        logger=logger,
        on_error=on_error,
    )

    assert erros == ["ValueError"]
    logger.error.assert_not_called()
    assert sleep_mock.await_count == 1


@pytest.mark.asyncio
async def test_safe_loop_hooks_e_cancelamento() -> None:
    on_start = AsyncMock()
    on_stop = AsyncMock()
    logger = MagicMock()

    async def iteration_fn() -> None:
        raise asyncio.CancelledError

    await safe_loop(
        iteration_fn,
        interval=1.0,
        logger=logger,
        on_start=on_start,
        on_stop=on_stop,
    )

    on_start.assert_awaited_once()
    on_stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_safe_loop_on_start_falha_e_aborta() -> None:
    logger = MagicMock()
    iteration_fn = AsyncMock()

    async def on_start() -> None:
        raise RuntimeError("start failed")

    with pytest.raises(RuntimeError, match="start failed"):
        await safe_loop(
            iteration_fn,
            interval=1.0,
            logger=logger,
            on_start=on_start,
        )

    iteration_fn.assert_not_awaited()


@pytest.mark.asyncio
async def test_safe_loop_on_stop_falha_e_e_suprimido(monkeypatch) -> None:
    logger = MagicMock()

    async def iteration_fn() -> None:
        raise asyncio.CancelledError

    async def on_stop() -> None:
        raise RuntimeError("cleanup failed")

    sleep_mock = AsyncMock()
    monkeypatch.setattr("src.common.loops.asyncio.sleep", sleep_mock)

    await safe_loop(
        iteration_fn,
        interval=1.0,
        logger=logger,
        on_stop=on_stop,
    )

    logger.error.assert_called_once()
    args, kwargs = logger.error.call_args
    assert args[0] == "safe_loop_on_stop_error"
    assert kwargs["error_type"] == "RuntimeError"
