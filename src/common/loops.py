from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any


async def safe_loop(
    iteration_fn: Callable[[], Awaitable[Any]],
    *,
    interval: float,
    logger: Any,
    error_event: str = "safe_loop_error",
    loop_name: str | None = None,
    on_start: Callable[[], Awaitable[Any]] | None = None,
    on_stop: Callable[[], Awaitable[Any]] | None = None,
    on_error: Callable[[BaseException], None] | None = None,
) -> None:
    """Executa iteration_fn em loop assíncrono com tratamento padronizado de erros.

    Args:
        iteration_fn: Coroutine chamada a cada iteração.
        interval: Segundos entre o fim de uma iteração e o início da próxima.
        logger: Instância de logger estruturado.
        error_event: Nome do evento de log em caso de erro.
        loop_name: Identificador opcional para logs.
        on_start: Coroutine opcional executada antes do loop.
        on_stop: Coroutine opcional executada após o loop (cleanup).
        on_error: Callback opcional para tratar exceções da iteração.

    Exceptions:
        CancelledError: interrompe o loop silenciosamente.
        Qualquer outra: logada via logger.error com error_event quando on_error
        não for fornecido; o loop continua na próxima iteração.
    """
    if interval <= 0:
        raise ValueError("interval must be greater than 0")

    if on_start is not None:
        await on_start()

    while True:
        try:
            await iteration_fn()
        except asyncio.CancelledError:
            if on_stop is not None:
                try:
                    await on_stop()
                except Exception as stop_exc:
                    logger.error(
                        "safe_loop_on_stop_error",
                        loop_name=loop_name,
                        error_type=type(stop_exc).__name__,
                        exc_info=True,
                    )
            return
        except Exception as exc:
            if on_error is not None:
                on_error(exc)
            else:
                logger.error(
                    error_event,
                    loop_name=loop_name,
                    error_type=type(exc).__name__,
                    exc_info=True,
                )

        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            if on_stop is not None:
                try:
                    await on_stop()
                except Exception as stop_exc:
                    logger.error(
                        "safe_loop_on_stop_error",
                        loop_name=loop_name,
                        error_type=type(stop_exc).__name__,
                        exc_info=True,
                    )
            return
