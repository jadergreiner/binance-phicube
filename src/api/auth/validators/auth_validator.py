"""Auth Validator interface - Chain of Responsibility Pattern.

Interface para validadores de autenticação encadeados.
Permite adicionar novas regras de validação sem modificar código existente.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Resultado da validação."""

    valid: bool
    error: str | None = None


class AuthValidator(ABC):
    """Interface abstrata para validadores de autenticação."""

    _next: "AuthValidator | None" = None

    def set_next(self, validator: "AuthValidator") -> "AuthValidator":
        """Define o próximo validador na cadeia."""
        self._next = validator
        return validator

    async def validate(self, email: str) -> ValidationResult:
        """Valida o email através da cadeia de validadores."""
        result = await self._validate(email)
        if not result.valid and self._next:
            return await self._next.validate(email)
        return result

    @abstractmethod
    async def _validate(self, email: str) -> ValidationResult:
        """Implementa a lógica de validação específica."""
        pass