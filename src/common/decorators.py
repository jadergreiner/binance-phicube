"""Decoradores utilitários para tratamento seguro de erros e retry.

Padrões centralizados:
- _safe_call: compatível com api/main.py existente
- @safe_async: decorador para funções async com fallback seguro
- @retry: retry com backoff exponencial (levanta exceção após esgotar)
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar

from src.monitoring.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")
P = ParamSpec("P")


# --- Utilitário _safe_call (API COMPATÍVEL com src/api/main.py) ---


async def _safe_call(
    coro: Awaitable[Any],
    *,
    warning_message: str,
    logger_func: Callable[..., Any] | None = None,
    exc_types: tuple[type[BaseException], ...] = (Exception,),
) -> bool:
    """Executa corotina de forma segura, loga warning em caso de erro.

    API idêntica à versão anterior em src/api/main.py para compatibilidade.
    NÃO loga str(exc) — usa type(exc).__name__ para segurança (Telegram token).

    Args:
        coro: Corotina a executar
        warning_message: Chave de evento para structlog
        logger_func: Função de log customizada (padrão: logger.warning)
        exc_types: Tipos de exceção a capturar (padrão: Exception)

    Returns:
        True se sucesso, False se exceção capturada
    """
    try:
        await coro
        return True
    except exc_types as exc:
        log_fn = logger_func or logger.warning
        log_fn(warning_message, error_type=type(exc).__name__)
        return False


# --- Decorador @safe_async ---


def safe_async(
    *,
    log_event: str,
    fallback: Any = None,
    exc_types: tuple[type[BaseException], ...] = (Exception,),
    logger_func: Callable[..., Any] | None = None,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T | Any]]]:
    """Decorador para funções async: captura exceções, loga com segurança, retorna fallback.

    NÃO loga str(exc) — usa type(exc).__name__ para evitar vazamento de tokens.

    Exemplo:
        @safe_async(log_event="repo_query_failed", fallback={})
        async def get_data():
            return await db.query()

    Args:
        log_event: Chave de evento para structlog
        fallback: Valor a retornar em caso de exceção
        exc_types: Tupla de tipos de exceção a capturar
        logger_func: Função de log customizada (padrão: logger.warning)

    Returns:
        Decorador
    """

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T | Any]]:
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | Any:
            try:
                return await func(*args, **kwargs)
            except exc_types as exc:
                log_fn = logger_func or logger.warning
                log_fn(log_event, error_type=type(exc).__name__)
                return fallback

        return wrapper

    return decorator


# --- Decorador @retry (levanta exceção após max_attempts: OPÇÃO A) ---


def retry(
    *,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exc_types: tuple[type[BaseException], ...] = (Exception,),
    log_event_prefix: str = "operation",
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Decorador para retry com backoff exponencial.

    LEVANTA EXCEÇÃO após esgotar tentativas (não silencia erros).
    Útil para chamadas de rede onde falha deve ser conhecida pelo chamador.

    Logs estruturados:
    - {prefix}_attempt: loga cada tentativa (1-based)
    - {prefix}_retry_wait: loga delay antes da próxima tentativa

    Exemplo:
        @retry(
            max_attempts=3,
            exc_types=(asyncio.TimeoutError, aiohttp.ClientError),
            log_event_prefix="telegram_send"
        )
        async def send_message():
            ...

    Args:
        max_attempts: Número máximo de tentativas
        initial_delay: Delay inicial em segundos (primeiro backoff)
        backoff_factor: Multiplicador para backoff (2.0 = exponencial: 1s, 2s, 4s)
        exc_types: Exceções que disparam retry
        log_event_prefix: Prefixo para chaves de log estruturado

    Returns:
        Decorador
    """

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exc: BaseException | None = None

            for attempt in range(max_attempts):
                attempt_1based = attempt + 1

                try:
                    logger.debug(f"{log_event_prefix}_attempt", attempt=attempt_1based)
                    return await func(*args, **kwargs)

                except exc_types as exc:
                    last_exc = exc
                    logger.warning(
                        f"{log_event_prefix}_failed",
                        attempt=attempt_1based,
                        error_type=type(exc).__name__,
                    )

                    # Ainda tem tentativas? Espera backoff
                    if attempt < max_attempts - 1:
                        delay = initial_delay * (backoff_factor**attempt)
                        logger.debug(
                            f"{log_event_prefix}_retry_wait",
                            next_attempt=attempt_1based + 1,
                            delay_seconds=delay,
                        )
                        await asyncio.sleep(delay)

            # Esgotou todas as tentativas: LEVANTA EXCEÇÃO (OPÇÃO A)
            assert last_exc is not None
            logger.error(
                f"{log_event_prefix}_exhausted",
                max_attempts=max_attempts,
                last_error_type=type(last_exc).__name__,
            )
            raise last_exc

        return wrapper

    return decorator
