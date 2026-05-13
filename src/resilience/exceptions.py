"""Exceções customizadas para o módulo resilience."""


class CircuitBreakerOpenError(Exception):
    """Exceção levantada quando CircuitBreaker está OPEN."""

    pass
