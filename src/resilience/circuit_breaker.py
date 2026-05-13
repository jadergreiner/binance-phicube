"""CircuitBreaker para resiliência e recuperação de falhas."""

import time
from dataclasses import dataclass, field
from enum import StrEnum


class CircuitBreakerState(StrEnum):
    """Estados possíveis do CircuitBreaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """
    Dataclass representando um CircuitBreaker.

    Atributos:
        name: identificador único do circuit breaker
        state: estado atual (CLOSED, OPEN, HALF_OPEN)
        failure_count: número de falhas consecutivas
        last_failure_time: timestamp da última falha (segundos desde epoch)
        failure_threshold: limite de falhas antes de abrir (default=3)
        recovery_timeout: tempo de espera antes de tentar half-open (default=60.0 segundos)
        last_state_change: timestamp da última mudança de estado (segundos desde epoch)
    """

    name: str
    state: CircuitBreakerState
    failure_count: int
    last_failure_time: float
    failure_threshold: int = 3
    recovery_timeout: float = 60.0
    last_state_change: float = field(default_factory=time.time)

    def can_attempt_half_open(self) -> bool:
        """Verifica se é possível tentar transição para HALF_OPEN."""
        if self.state != CircuitBreakerState.OPEN:
            return False
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.recovery_timeout

    def record_success(self) -> None:
        """Registra sucesso, resetando falhas se em HALF_OPEN."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.CLOSED
            self.failure_count = 0
            self.last_state_change = time.time()

    def record_failure(self) -> None:
        """Registra falha e potencialmente abre o circuit breaker."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            if self.state != CircuitBreakerState.OPEN:
                self.state = CircuitBreakerState.OPEN
                self.last_state_change = time.time()

    def attempt_half_open(self) -> None:
        """Transiciona para HALF_OPEN se timeout expirou."""
        if self.can_attempt_half_open():
            self.state = CircuitBreakerState.HALF_OPEN
            self.last_state_change = time.time()


class CircuitBreakerRegistry:
    """
    Registry para gerenciar múltiplas instâncias de CircuitBreaker.

    Fornece acesso centralizado, idempotente a circuit breakers.
    """

    def __init__(self, namespace: str | None = None) -> None:
        """
        Inicializa o registry.

        Args:
            namespace: prefixo opcional para future-proofing (não usado atualmente)
        """
        self._breakers: dict[str, CircuitBreaker] = {}
        self.namespace = namespace

    def get(self, name: str, recovery_timeout: float | None = None) -> CircuitBreaker:
        """
        Obtém ou cria um CircuitBreaker.

        Idempotente: chamadas sucessivas com mesmo name retornam a mesma instância.

        Args:
            name: identificador único do circuit breaker
            recovery_timeout: timeout de recuperação (sobrescreve default se fornecido)

        Returns:
            CircuitBreaker existente ou recém-criado
        """
        if name in self._breakers:
            return self._breakers[name]

        timeout = recovery_timeout if recovery_timeout is not None else 60.0

        breaker = CircuitBreaker(
            name=name,
            state=CircuitBreakerState.CLOSED,
            failure_count=0,
            last_failure_time=time.time(),
            recovery_timeout=timeout,
        )

        self._breakers[name] = breaker
        return breaker

    def state_summary(self) -> dict[str, str]:
        """
        Retorna um sumário dos estados dos circuit breakers.

        Returns:
            dict com nomes como chaves e valores de estado como strings
            (ex: {'service_a': 'closed', 'service_b': 'open'})
        """
        return {name: breaker.state.value for name, breaker in self._breakers.items()}
