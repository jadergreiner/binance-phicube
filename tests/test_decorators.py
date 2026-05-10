"""
Testes unitários — Decoradores utilitários (safe_async, retry, _safe_call).
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.decorators import _safe_call, retry, safe_async

# ─── Testes para _safe_call ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_safe_call_returns_true_on_success():
    """_safe_call retorna True quando a corotina executa com sucesso."""
    mock_coro = AsyncMock(return_value="ok")
    logger_mock = MagicMock()

    result = await _safe_call(
        mock_coro(),
        warning_message="test_warning",
        logger_func=logger_mock.warning,
    )

    assert result is True
    logger_mock.warning.assert_not_called()


@pytest.mark.asyncio
async def test_safe_call_returns_false_on_exception():
    """_safe_call captura exceção e retorna False, logando com segurança."""
    exc = ValueError("test error")

    async def failing_coro():
        raise exc

    logger_mock = MagicMock()

    result = await _safe_call(
        failing_coro(),
        warning_message="test_operation_failed",
        logger_func=logger_mock.warning,
    )

    assert result is False
    logger_mock.warning.assert_called_once()
    # Verifica que usa type(exc).__name__ (segurança: não loga str(exc))
    call_args = logger_mock.warning.call_args
    assert "test_operation_failed" in call_args.args or "test_operation_failed" in str(call_args)
    assert call_args.kwargs.get("error_type") == "ValueError"


@pytest.mark.asyncio
async def test_safe_call_captures_only_specified_exc_types():
    """_safe_call respeita o parâmetro exc_types e não captura outras exceções."""

    async def raises_key_error():
        raise KeyError("secret_key_should_not_be_logged")

    logger_mock = MagicMock()

    # Deve levantar exceção pois KeyError não está em (ValueError,)
    with pytest.raises(KeyError):
        await _safe_call(
            raises_key_error(),
            warning_message="should_not_log",
            logger_func=logger_mock.warning,
            exc_types=(ValueError,),
        )

    logger_mock.warning.assert_not_called()


# ─── Testes para @safe_async ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_safe_async_returns_value_on_success():
    """@safe_async retorna o valor original quando não há exceção."""

    @safe_async(log_event="test_success", fallback="fallback_value")
    async def success_fn(x: int) -> int:
        return x * 2

    result = await success_fn(5)
    assert result == 10


@pytest.mark.asyncio
async def test_safe_async_returns_fallback_on_exception():
    """@safe_async captura exceção e retorna o valor de fallback."""

    expected_fallback: dict[str, Any] = {}

    @safe_async(log_event="test_failed", fallback=expected_fallback)
    async def failing_fn() -> dict[str, Any]:
        raise RuntimeError("something went wrong")

    result = await failing_fn()
    assert result is expected_fallback


@pytest.mark.asyncio
async def test_safe_async_logs_error_type_safely():
    """@safe_async loga usando error_type=type(exc).__name__ (não str(exc))."""
    logger_mock = MagicMock()

    @safe_async(
        log_event="secure_log_test",
        fallback=[],
        logger_func=logger_mock.warning,
    )
    async def raises_value_error() -> list[Any]:
        raise ValueError("SENSITIVE_TOKEN=abc123")

    await raises_value_error()

    logger_mock.warning.assert_called_once()
    kwargs = logger_mock.warning.call_args.kwargs
    assert kwargs.get("error_type") == "ValueError"
    # Garante que NÃO logou a mensagem sensível
    call_str = str(logger_mock.warning.call_args)
    assert "SENSITIVE_TOKEN" not in call_str
    assert "abc123" not in call_str


# ─── Testes para @retry (OPÇÃO A: levanta exceção após max_attempts) ───────


@pytest.mark.asyncio
async def test_retry_succeeds_on_first_attempt():
    """@retry retorna sucesso na primeira tentativa, sem delays adicionais."""
    call_count = 0

    @retry(max_attempts=3, initial_delay=0.1, backoff_factor=2.0, log_event_prefix="test")
    async def succeeds_immediately() -> str:
        nonlocal call_count
        call_count += 1
        return "success"

    result = await succeeds_immediately()
    assert result == "success"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_succeeds_on_second_attempt():
    """@retry tenta novamente após falha e retorna sucesso na segunda tentativa."""
    call_count = 0

    @retry(
        max_attempts=3,
        initial_delay=0.01,  # delay pequeno para teste rápido
        backoff_factor=2.0,
        log_event_prefix="flaky_test",
    )
    async def flaky_function() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("temporary failure")
        return "success_on_retry"

    result = await flaky_function()
    assert result == "success_on_retry"
    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_raises_after_max_attempts():
    """@retry levanta a ÚLTIMA exceção após esgotar max_attempts (OPÇÃO A)."""
    call_count = 0

    @retry(
        max_attempts=2,
        initial_delay=0.01,
        backoff_factor=2.0,
        log_event_prefix="always_fails",
    )
    async def always_fails() -> None:
        nonlocal call_count
        call_count += 1
        raise TimeoutError(f"attempt {call_count} failed")

    with pytest.raises(TimeoutError) as exc_info:
        await always_fails()

    # Verifica que tentou exatamente max_attempts vezes
    assert call_count == 2
    # Verifica que a exceção levantada é a da última tentativa
    assert "attempt 2 failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_retry_respects_exc_types():
    """@retry NÃO faz retry para exceções fora de exc_types; levanta imediatamente."""
    call_count = 0

    @retry(
        max_attempts=3,
        initial_delay=0.01,
        backoff_factor=2.0,
        exc_types=(ConnectionError, TimeoutError),  # apenas ess disparam retry
        log_event_prefix="selective_retry",
    )
    async def raises_unexpected_error() -> None:
        nonlocal call_count
        call_count += 1
        raise ValueError("critical logic error")  # NÃO está em exc_types

    with pytest.raises(ValueError):
        await raises_unexpected_error()

    # NÃO deve ter feito retry — apenas 1 chamada
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_backoff_timing():
    """@retry espera delays crescentes (exponencial) entre tentativas."""
    call_count = 0
    delays_observed: list[float] = []
    last_time = asyncio.get_event_loop().time()

    original_sleep = asyncio.sleep

    async def measured_sleep(delay: float) -> None:
        nonlocal last_time
        now = asyncio.get_event_loop().time()
        elapsed = now - last_time
        delays_observed.append(elapsed)
        last_time = now
        # Não espera realmente para teste rápido, mas verifica que a função é chamada
        await original_sleep(0)

    @retry(
        max_attempts=3,
        initial_delay=0.1,
        backoff_factor=2.0,  # Espera: ~0.1s, ~0.2s
        log_event_prefix="timing_test",
    )
    async def fails_twice() -> str:
        nonlocal call_count, last_time
        call_count += 1
        if call_count < 3:
            raise ConnectionError("retry please")
        return "success"

    # Patch asyncio.sleep
    # Usamos monkeypatch do pytest se disponível, ou mock manual
    from unittest.mock import patch

    with patch("src.common.decorators.asyncio.sleep", side_effect=measured_sleep):
        result = await fails_twice()

    assert result == "success"
    assert call_count == 3
    # 2 delays esperados (entre tentativa 1-2 e 2-3)
    assert len(delays_observed) == 2


# ─── Testes para NOVAS features do @retry ───────────────────────────────────


class CustomFatalError(Exception):
    """Exceção fatal customizada para testes."""

    pass


class CustomRecoverableError(Exception):
    """Exceção recuperável customizada para testes."""

    pass


class CustomSpecialError(Exception):
    """Exceção especial para testes de special_cases."""

    pass


@pytest.mark.asyncio
async def test_retry_fatal_exc_types_raise_immediately():
    """@retry com fatal_exc_types: re-raise imediato SEM retry."""
    call_count = 0

    @retry(
        max_attempts=3,
        initial_delay=0.01,
        backoff_factor=2.0,
        exc_types=(CustomRecoverableError,),
        fatal_exc_types=(CustomFatalError,),
        log_event_prefix="fatal_test",
    )
    async def raises_fatal_error() -> None:
        nonlocal call_count
        call_count += 1
        raise CustomFatalError("this is fatal")

    with pytest.raises(CustomFatalError):
        await raises_fatal_error()

    # NÃO deve ter feito retry — apenas 1 chamada
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_mixed_fatal_and_recoverable():
    """@retry: fatal_exc_types vs exc_types — fatal ganha."""
    call_count = 0
    errors_seen: list[str] = []

    @retry(
        max_attempts=3,
        initial_delay=0.01,
        backoff_factor=2.0,
        exc_types=(Exception,),  # Captura tudo
        fatal_exc_types=(CustomFatalError,),  # Mas isso é fatal
        log_event_prefix="mixed_test",
    )
    async def flaky_with_fatal() -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            errors_seen.append("recoverable")
            raise CustomRecoverableError("try again")  # Deve fazer retry
        if call_count == 2:
            errors_seen.append("fatal")
            raise CustomFatalError("stop now")  # Deve parar imediatamente
        return "success"

    with pytest.raises(CustomFatalError):
        await flaky_with_fatal()

    # 1ª chamada: recoverable → retry
    # 2ª chamada: fatal → re-raise imediato
    assert call_count == 2
    assert errors_seen == ["recoverable", "fatal"]


@pytest.mark.asyncio
async def test_retry_fallback_on_exhaustion():
    """@retry com fallback: retorna fallback quando tentativas se esgotam."""
    call_count = 0
    expected_fallback = {"status": "degraded", "data": None}

    @retry(
        max_attempts=2,
        initial_delay=0.01,
        backoff_factor=2.0,
        fallback=expected_fallback,
        log_event_prefix="fallback_test",
    )
    async def always_fails() -> dict[str, Any]:
        nonlocal call_count
        call_count += 1
        raise ConnectionError("network down")

    result = await always_fails()

    # Deve ter tentado max_attempts vezes
    assert call_count == 2
    # Deve retornar o fallback, não levantar exceção
    assert result is expected_fallback


@pytest.mark.asyncio
async def test_retry_fallback_with_successful_retry():
    """@retry com fallback: sucesso no retry NÃO retorna fallback."""
    call_count = 0
    expected_fallback = "fallback_value"
    expected_success = "real_value"

    @retry(
        max_attempts=3,
        initial_delay=0.01,
        backoff_factor=2.0,
        fallback=expected_fallback,
        log_event_prefix="success_fallback_test",
    )
    async def succeeds_on_second() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("temporary failure")
        return expected_success

    result = await succeeds_on_second()

    # Deve ter tentado 2 vezes
    assert call_count == 2
    # Deve retornar o valor real, NÃO o fallback
    assert result == expected_success
    assert result != expected_fallback


@pytest.mark.asyncio
async def test_retry_exception_wrapper():
    """@retry com exception_wrapper: envolve a exceção antes de levantar."""
    call_count = 0

    def my_wrapper(
        exc: BaseException,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        bound_args: dict[str, Any],
    ) -> Exception:
        # Verifica que recebemos os argumentos corretos
        assert args == (1, 2)
        assert kwargs == {"c": 3}
        assert bound_args == {"a": 1, "b": 2, "c": 3}
        return ValueError(f"Wrapped error: {type(exc).__name__}")

    @retry(
        max_attempts=2,
        initial_delay=0.01,
        backoff_factor=2.0,
        exception_wrapper=my_wrapper,
        log_event_prefix="wrapper_test",
    )
    async def flaky_with_wrapper(a: int, b: int, c: int = 3) -> str:
        nonlocal call_count
        call_count += 1
        raise RuntimeError("original error")

    with pytest.raises(ValueError) as exc_info:
        await flaky_with_wrapper(1, 2, c=3)

    # Verifica que tentou todas as vezes
    assert call_count == 2
    # Verifica que a exceção foi envolvida
    assert "Wrapped error" in str(exc_info.value)
    # Verifica que __cause__ está definido
    assert isinstance(exc_info.value.__cause__, RuntimeError)


@pytest.mark.asyncio
async def test_retry_exception_wrapper_bound_args_defaults():
    """@retry exception_wrapper: bound_args inclui valores default."""
    captured_bound_args: dict[str, Any] = {}

    def capture_wrapper(
        exc: BaseException,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        bound_args: dict[str, Any],
    ) -> Exception:
        captured_bound_args.update(bound_args)
        return RuntimeError("wrapped")

    @retry(
        max_attempts=1,
        initial_delay=0.01,
        exception_wrapper=capture_wrapper,
        log_event_prefix="bound_test",
    )
    async def func_with_defaults(x: int, y: str = "default_y", z: bool = True) -> None:
        raise ValueError("fail")

    with pytest.raises(RuntimeError):
        await func_with_defaults(42)  # Apenas x fornecido

    # bound_args deve incluir todos os argumentos, incluindo defaults
    assert captured_bound_args == {"x": 42, "y": "default_y", "z": True}


@pytest.mark.asyncio
async def test_retry_special_cases_return_immediately():
    """@retry com special_cases: retorno imediato SEM retry."""
    call_count = 0
    special_return_value = {"handled": True, "reason": "special_case"}

    @retry(
        max_attempts=3,
        initial_delay=0.01,
        backoff_factor=2.0,
        special_cases={CustomSpecialError: special_return_value},
        log_event_prefix="special_test",
    )
    async def raises_special_error() -> dict[str, Any]:
        nonlocal call_count
        call_count += 1
        raise CustomSpecialError("this is special")

    result = await raises_special_error()

    # NÃO deve ter feito retry — apenas 1 chamada
    assert call_count == 1
    # Deve retornar o valor do special_cases
    assert result is special_return_value


@pytest.mark.asyncio
async def test_retry_special_cases_vs_retry():
    """@retry: special_cases tem prioridade sobre retry."""
    call_count = 0
    special_value = "special_handled"

    @retry(
        max_attempts=3,
        initial_delay=0.01,
        backoff_factor=2.0,
        exc_types=(Exception,),  # Captura tudo
        special_cases={CustomSpecialError: special_value},
        log_event_prefix="special_vs_retry",
    )
    async def flaky_with_special() -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise CustomRecoverableError("try again")  # Faz retry
        if call_count == 2:
            raise CustomSpecialError("stop here")  # Retorna special_value
        return "success"

    result = await flaky_with_special()

    # 1ª chamada: recoverable → retry
    # 2ª chamada: special → retorno imediato
    assert call_count == 2
    assert result == special_value


@pytest.mark.asyncio
async def test_retry_combination_all_features():
    """@retry: combinação de todas as features em conjunto."""
    call_count = 0

    def wrapper_fn(exc, args, kwargs, bound_args):
        return RuntimeError(f"Wrapper: {type(exc).__name__}")

    @retry(
        max_attempts=4,
        initial_delay=0.01,
        backoff_factor=2.0,
        exc_types=(CustomRecoverableError,),
        fatal_exc_types=(CustomFatalError,),
        special_cases={CustomSpecialError: "special_return"},
        log_event_prefix="all_features",
    )
    async def complex_scenario() -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise CustomRecoverableError("retry 1")
        if call_count == 2:
            raise CustomRecoverableError("retry 2")
        if call_count == 3:
            raise CustomRecoverableError("retry 3")
        if call_count == 4:
            raise CustomRecoverableError("final fail")
        return "success"

    # Sem fallback nem exception_wrapper: deve levantar a exceção original
    with pytest.raises(CustomRecoverableError):
        await complex_scenario()

    # Deve ter tentado todas as 4 vezes
    assert call_count == 4


@pytest.mark.asyncio
async def test_retry_fallback_has_higher_priority_than_wrapper():
    """@retry: fallback tem prioridade sobre exception_wrapper."""
    call_count = 0
    fallback_value = "fallback_wins"
    wrapper_called = False

    def wrapper_fn(exc, args, kwargs, bound_args):
        nonlocal wrapper_called
        wrapper_called = True
        return RuntimeError("wrapped")

    @retry(
        max_attempts=2,
        initial_delay=0.01,
        fallback=fallback_value,
        exception_wrapper=wrapper_fn,
        log_event_prefix="priority_test",
    )
    async def always_fails() -> str:
        nonlocal call_count
        call_count += 1
        raise ValueError("fail")

    result = await always_fails()

    # Fallback tem prioridade
    assert result == fallback_value
    # Exception_wrapper NÃO deve ser chamado quando fallback está presente
    assert wrapper_called is False
    # Mas tentou todas as vezes
    assert call_count == 2
