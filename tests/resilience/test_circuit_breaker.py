"""Testes para CircuitBreaker e CircuitBreakerRegistry."""

import time

import pytest

from src.resilience import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitBreakerRegistry,
    CircuitBreakerState,
)


class TestCircuitBreakerState:
    """Testes para CircuitBreakerState enum."""

    def test_state_values_are_lowercase_strings(self) -> None:
        """Verifica que os valores de estado são strings em lowercase."""
        assert CircuitBreakerState.CLOSED.value == "closed"
        assert CircuitBreakerState.OPEN.value == "open"
        assert CircuitBreakerState.HALF_OPEN.value == "half_open"

    def test_state_enum_members_accessible(self) -> None:
        """Verifica que todos os estados são acessíveis."""
        assert CircuitBreakerState.CLOSED is not None
        assert CircuitBreakerState.OPEN is not None
        assert CircuitBreakerState.HALF_OPEN is not None

    def test_state_comparison_with_equality(self) -> None:
        """Verifica comparação entre estados com ==."""
        assert CircuitBreakerState.CLOSED == CircuitBreakerState.CLOSED
        assert CircuitBreakerState.OPEN == CircuitBreakerState.OPEN
        assert CircuitBreakerState.HALF_OPEN == CircuitBreakerState.HALF_OPEN
        assert CircuitBreakerState.CLOSED != CircuitBreakerState.OPEN


class TestCircuitBreaker:
    """Testes para CircuitBreaker dataclass."""

    def test_circuit_breaker_initialization(self) -> None:
        """Verifica inicialização básica do CircuitBreaker."""
        cb = CircuitBreaker(
            name="test_service",
            state=CircuitBreakerState.CLOSED,
            failure_count=0,
            last_failure_time=time.time(),
        )
        assert cb.name == "test_service"
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 60.0

    def test_circuit_breaker_custom_threshold_and_timeout(self) -> None:
        """Verifica inicialização com threshold e timeout customizados."""
        now = time.time()
        cb = CircuitBreaker(
            name="custom_service",
            state=CircuitBreakerState.CLOSED,
            failure_count=0,
            last_failure_time=now,
            failure_threshold=5,
            recovery_timeout=30.0,
        )
        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 30.0

    def test_record_failure_increments_count(self) -> None:
        """Verifica que record_failure incrementa failure_count."""
        cb = CircuitBreaker(
            name="test",
            state=CircuitBreakerState.CLOSED,
            failure_count=0,
            last_failure_time=time.time(),
        )
        cb.record_failure()
        assert cb.failure_count == 1
        cb.record_failure()
        assert cb.failure_count == 2

    def test_record_failure_opens_circuit_on_threshold(self) -> None:
        """Verifica que circuit breaker abre após threshold de falhas."""
        cb = CircuitBreaker(
            name="test",
            state=CircuitBreakerState.CLOSED,
            failure_count=0,
            last_failure_time=time.time(),
            failure_threshold=3,
        )
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

    def test_record_success_closes_circuit_from_half_open(self) -> None:
        """Verifica que sucesso em HALF_OPEN fecha o circuit breaker."""
        cb = CircuitBreaker(
            name="test",
            state=CircuitBreakerState.HALF_OPEN,
            failure_count=5,
            last_failure_time=time.time(),
        )
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    def test_record_success_no_change_when_closed(self) -> None:
        """Verifica que sucesso em CLOSED não muda estado."""
        cb = CircuitBreaker(
            name="test",
            state=CircuitBreakerState.CLOSED,
            failure_count=0,
            last_failure_time=time.time(),
        )
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED

    def test_can_attempt_half_open_when_timeout_expired(self) -> None:
        """Verifica can_attempt_half_open retorna True após timeout."""
        past_time = time.time() - 61.0  # 61 segundos atrás
        cb = CircuitBreaker(
            name="test",
            state=CircuitBreakerState.OPEN,
            failure_count=3,
            last_failure_time=past_time,
            recovery_timeout=60.0,
        )
        assert cb.can_attempt_half_open() is True

    def test_can_attempt_half_open_when_timeout_not_expired(self) -> None:
        """Verifica can_attempt_half_open retorna False durante timeout."""
        recent_time = time.time() - 30.0  # 30 segundos atrás
        cb = CircuitBreaker(
            name="test",
            state=CircuitBreakerState.OPEN,
            failure_count=3,
            last_failure_time=recent_time,
            recovery_timeout=60.0,
        )
        assert cb.can_attempt_half_open() is False

    def test_can_attempt_half_open_returns_false_when_not_open(self) -> None:
        """Verifica que can_attempt_half_open retorna False quando não OPEN."""
        cb = CircuitBreaker(
            name="test",
            state=CircuitBreakerState.CLOSED,
            failure_count=0,
            last_failure_time=time.time(),
        )
        assert cb.can_attempt_half_open() is False

        cb_half_open = CircuitBreaker(
            name="test",
            state=CircuitBreakerState.HALF_OPEN,
            failure_count=1,
            last_failure_time=time.time(),
        )
        assert cb_half_open.can_attempt_half_open() is False

    def test_attempt_half_open_transitions_state(self) -> None:
        """Verifica que attempt_half_open transiciona para HALF_OPEN."""
        past_time = time.time() - 61.0
        cb = CircuitBreaker(
            name="test",
            state=CircuitBreakerState.OPEN,
            failure_count=3,
            last_failure_time=past_time,
            recovery_timeout=60.0,
        )
        cb.attempt_half_open()
        assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_attempt_half_open_no_change_when_timeout_not_expired(self) -> None:
        """Verifica que attempt_half_open não muda estado se timeout não expirou."""
        recent_time = time.time() - 30.0
        cb = CircuitBreaker(
            name="test",
            state=CircuitBreakerState.OPEN,
            failure_count=3,
            last_failure_time=recent_time,
            recovery_timeout=60.0,
        )
        cb.attempt_half_open()
        assert cb.state == CircuitBreakerState.OPEN

    def test_last_failure_time_updated_on_record_failure(self) -> None:
        """Verifica que last_failure_time é atualizado ao registrar falha."""
        cb = CircuitBreaker(
            name="test",
            state=CircuitBreakerState.CLOSED,
            failure_count=0,
            last_failure_time=time.time() - 100,
        )
        before = time.time()
        cb.record_failure()
        after = time.time()
        assert before <= cb.last_failure_time <= after

    def test_last_state_change_updated_on_open(self) -> None:
        """Verifica que last_state_change é atualizado ao abrir circuit."""
        cb = CircuitBreaker(
            name="test",
            state=CircuitBreakerState.CLOSED,
            failure_count=0,
            last_failure_time=time.time(),
            failure_threshold=1,
        )
        before = time.time()
        cb.record_failure()
        after = time.time()
        assert before <= cb.last_state_change <= after


class TestCircuitBreakerRegistry:
    """Testes para CircuitBreakerRegistry."""

    def test_registry_initialization(self) -> None:
        """Verifica inicialização da registry."""
        registry = CircuitBreakerRegistry()
        assert registry.namespace is None
        assert len(registry._breakers) == 0

    def test_registry_initialization_with_namespace(self) -> None:
        """Verifica inicialização com namespace."""
        registry = CircuitBreakerRegistry(namespace="api_services")
        assert registry.namespace == "api_services"

    def test_get_creates_new_circuit_breaker(self) -> None:
        """Verifica que get() cria novo circuit breaker."""
        registry = CircuitBreakerRegistry()
        cb = registry.get("service_a")
        assert cb.name == "service_a"
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.recovery_timeout == 60.0

    def test_get_is_idempotent(self) -> None:
        """Verifica que get() retorna mesma instância para mesmo name."""
        registry = CircuitBreakerRegistry()
        cb1 = registry.get("service_a")
        cb2 = registry.get("service_a")
        assert cb1 is cb2

    def test_get_with_custom_recovery_timeout(self) -> None:
        """Verifica que recovery_timeout customizado é aplicado."""
        registry = CircuitBreakerRegistry()
        cb = registry.get("service_a", recovery_timeout=30.0)
        assert cb.recovery_timeout == 30.0

    def test_get_recovery_timeout_not_overridden_on_second_call(self) -> None:
        """Verifica que recovery_timeout não é sobrescrito em segundo get()."""
        registry = CircuitBreakerRegistry()
        cb1 = registry.get("service_a", recovery_timeout=30.0)
        cb2 = registry.get("service_a", recovery_timeout=90.0)
        assert cb1 is cb2
        assert cb2.recovery_timeout == 30.0

    def test_get_default_recovery_timeout(self) -> None:
        """Verifica que recovery_timeout padrão é 60.0."""
        registry = CircuitBreakerRegistry()
        cb = registry.get("service_a")
        assert cb.recovery_timeout == 60.0

    def test_multiple_circuit_breakers(self) -> None:
        """Verifica que múltiplos circuit breakers podem coexistir."""
        registry = CircuitBreakerRegistry()
        cb_a = registry.get("service_a")
        cb_b = registry.get("service_b")
        cb_c = registry.get("service_c")

        assert cb_a.name == "service_a"
        assert cb_b.name == "service_b"
        assert cb_c.name == "service_c"
        assert cb_a is not cb_b
        assert cb_b is not cb_c

    def test_state_summary_empty_registry(self) -> None:
        """Verifica state_summary em registry vazia."""
        registry = CircuitBreakerRegistry()
        summary = registry.state_summary()
        assert summary == {}

    def test_state_summary_with_single_breaker(self) -> None:
        """Verifica state_summary com um circuit breaker."""
        registry = CircuitBreakerRegistry()
        registry.get("service_a")
        summary = registry.state_summary()
        assert summary == {"service_a": "closed"}

    def test_state_summary_with_multiple_breakers(self) -> None:
        """Verifica state_summary com múltiplos circuit breakers."""
        registry = CircuitBreakerRegistry()
        registry.get("service_a")
        registry.get("service_b")
        cb_c = registry.get("service_c")
        cb_c.state = CircuitBreakerState.OPEN

        summary = registry.state_summary()
        assert summary == {
            "service_a": "closed",
            "service_b": "closed",
            "service_c": "open",
        }

    def test_state_summary_values_are_strings(self) -> None:
        """Verifica que values em state_summary são strings."""
        registry = CircuitBreakerRegistry()
        cb = registry.get("service_a")
        cb.state = CircuitBreakerState.HALF_OPEN

        summary = registry.state_summary()
        assert isinstance(summary["service_a"], str)
        assert summary["service_a"] == "half_open"

    def test_registry_no_exception_on_creation(self) -> None:
        """Verifica que nenhuma exceção é levantada ao criar registry."""
        registry = CircuitBreakerRegistry()
        cb1 = registry.get("service_a")
        cb2 = registry.get("service_b")
        assert cb1 is not None
        assert cb2 is not None


class TestCircuitBreakerOpenError:
    """Testes para CircuitBreakerOpenError."""

    def test_circuit_breaker_open_error_is_exception(self) -> None:
        """Verifica que CircuitBreakerOpenError é subclasse de Exception."""
        assert issubclass(CircuitBreakerOpenError, Exception)

    def test_circuit_breaker_open_error_can_be_raised(self) -> None:
        """Verifica que CircuitBreakerOpenError pode ser levantada."""
        with pytest.raises(CircuitBreakerOpenError):
            raise CircuitBreakerOpenError("Circuit breaker is open")

    def test_circuit_breaker_open_error_message(self) -> None:
        """Verifica mensagem da exceção."""
        msg = "Service unavailable: circuit breaker open"
        with pytest.raises(CircuitBreakerOpenError, match=msg):
            raise CircuitBreakerOpenError(msg)


class TestCircuitBreakerIntegration:
    """Testes de integração do CircuitBreaker."""

    def test_full_circuit_breaker_lifecycle(self) -> None:
        """Testa ciclo completo: CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""
        registry = CircuitBreakerRegistry()
        cb = registry.get("api_service", recovery_timeout=0.1)

        # Inicial: CLOSED
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

        # Registra falhas até abrir
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.failure_count == 3

        # Timeout expira, tenta HALF_OPEN
        time.sleep(0.15)
        cb.attempt_half_open()
        assert cb.state == CircuitBreakerState.HALF_OPEN

        # Sucesso em HALF_OPEN fecha
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    def test_registry_with_different_timeouts(self) -> None:
        """Testa registry com múltiplos breakers com timeouts diferentes."""
        registry = CircuitBreakerRegistry()
        cb_fast = registry.get("fast_service", recovery_timeout=10.0)
        cb_slow = registry.get("slow_service", recovery_timeout=120.0)

        assert cb_fast.recovery_timeout == 10.0
        assert cb_slow.recovery_timeout == 120.0
