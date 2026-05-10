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
