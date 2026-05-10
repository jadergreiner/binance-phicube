"""Decoradores utilitários para tratamento seguro de erros e retry.

Padrões centralizados:
- _safe_call: compatível com api/main.py existente
- @safe_async: decorador para funções async com fallback seguro
- @retry: retry com backoff exponencial (levanta exceção após esgotar)
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar

from src.monitoring.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")
P = ParamSpec("P")

# Sentinel para detectar quando fallback não foi fornecido
_NO_FALLBACK = object()


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
    # NOVOS PARÂMETROS:
    fatal_exc_types: tuple[type[BaseException], ...] = (),
    fallback: Any = _NO_FALLBACK,
    exception_wrapper: Callable[
        [BaseException, tuple[Any, ...], dict[str, Any], dict[str, Any]], BaseException
    ]
    | None = None,
    special_cases: dict[type[BaseException], Any] | None = None,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T | Any]]]:
    """Decorador para retry com backoff exponencial.

    LEVANTA EXCEÇÃO após esgotar tentativas (não silencia erros), a menos que
    `fallback` seja fornecido.

    Ordem de tratamento de exceções (prioridade):
    1. special_cases → retorno imediato SEM retry
    2. fatal_exc_types → re-raise imediato SEM retry
    3. exc_types → faz retry com backoff
    4. Outras exceções → re-raise imediato

    Quando tentativas exauridas:
    1. Se fallback fornecido → retorna fallback
    2. Se exception_wrapper fornecido → raise wrapper(exc) from exc
    3. Padrão → raise last_exc

    Logs estruturados:
    - {prefix}_attempt: loga cada tentativa (1-based)
    - {prefix}_special_case: loga quando special_cases é acionado
    - {prefix}_fatal_error: loga quando fatal_exc_types é acionado
    - {prefix}_failed: loga cada falha recuperável
    - {prefix}_retry_wait: loga delay antes da próxima tentativa
    - {prefix}_exhausted: loga quando tentativas se esgotam
    - {prefix}_exhausted_fallback: loga quando fallback é retornado
    - {prefix}_exhausted_wrapped: loga quando exception_wrapper é usado

    Exemplo:
        @retry(
            max_attempts=3,
            exc_types=(asyncio.TimeoutError, aiohttp.ClientError),
            fatal_exc_types=(ccxt.AuthenticationError, ccxt.InsufficientFunds),
            fallback=None,
            log_event_prefix="fetch_order"
        )
        async def fetch_order():
            ...

    Args:
        max_attempts: Número máximo de tentativas
        initial_delay: Delay inicial em segundos (primeiro backoff)
        backoff_factor: Multiplicador para backoff (2.0 = exponencial: 1s, 2s, 4s)
        exc_types: Exceções que disparam retry
        log_event_prefix: Prefixo para chaves de log estruturado
        fatal_exc_types: Exceções que devem ser re-raise imediatamente SEM retry
        fallback: Valor a retornar quando tentativas se esgotam (em vez de raise)
        exception_wrapper: Função para envolver a exceção final:
            (exc, args, kwargs, bound_args) -> Exception
            bound_args é um dict com todos os argumentos da função (usando inspect.signature)
        special_cases: Mapeamento {excecao: valor_retorno} para retorno imediato SEM retry

    Returns:
        Decorador
    """

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T | Any]]:
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | Any:
            last_exc: BaseException | None = None

            for attempt in range(max_attempts):
                attempt_1based = attempt + 1

                try:
                    logger.debug(f"{log_event_prefix}_attempt", attempt=attempt_1based)
                    return await func(*args, **kwargs)

                except BaseException as exc:
                    # 1. special_cases: retorno imediato SEM retry
                    if special_cases is not None:
                        for exc_type, return_value in special_cases.items():
                            if isinstance(exc, exc_type):
                                logger.info(
                                    f"{log_event_prefix}_special_case",
                                    error_type=type(exc).__name__,
                                    return_value_type=type(return_value).__name__,
                                )
                                return return_value

                    # 2. fatal_exc_types: re-raise imediato SEM retry
                    if isinstance(exc, fatal_exc_types):
                        logger.debug(
                            f"{log_event_prefix}_fatal_error",
                            error_type=type(exc).__name__,
                        )
                        raise

                    # 3. exc_types: faz retry com backoff
                    if isinstance(exc, exc_types):
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

                    # 4. Outras exceções: re-raise imediato
                    else:
                        raise

            # Esgotou todas as tentativas
            assert last_exc is not None

            # 1. Se fallback fornecido → retorna fallback
            if fallback is not _NO_FALLBACK:
                logger.warning(
                    f"{log_event_prefix}_exhausted_fallback",
                    max_attempts=max_attempts,
                    last_error_type=type(last_exc).__name__,
                    fallback_type=type(fallback).__name__,
                )
                return fallback

            # 2. Se exception_wrapper fornecido → usa wrapper com bound_args
            if exception_wrapper is not None:
                try:
                    sig = inspect.signature(func)
                    bound = sig.bind(*args, **kwargs)
                    bound.apply_defaults()
                    bound_args = dict(bound.arguments)
                except (ValueError, TypeError):
                    bound_args = {}

                logger.error(
                    f"{log_event_prefix}_exhausted_wrapped",
                    max_attempts=max_attempts,
                    last_error_type=type(last_exc).__name__,
                )
                wrapped_exc = exception_wrapper(last_exc, args, kwargs, bound_args)
                raise wrapped_exc from last_exc

            # 3. Padrão → raise original
            logger.error(
                f"{log_event_prefix}_exhausted",
                max_attempts=max_attempts,
                last_error_type=type(last_exc).__name__,
            )
            raise last_exc

        return wrapper

    return decorator
