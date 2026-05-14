"""Auth Strategy interface - Strategy Pattern.

Interface para estratégias de autenticação intercambiáveis.
Permite trocar OAuth por dev bypass ou fallback em runtime.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class AuthResult:
    """Resultado da autenticação."""

    success: bool
    token: str | None = None
    user: str | None = None
    error: str | None = None
    auth_method: str | None = None


class AuthStrategy(ABC):
    """Interface abstrata para estratégias de autenticação."""

    @abstractmethod
    async def authenticate(self, request: Any) -> AuthResult:
        """Autentica o usuário baseado na requisição."""

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Retorna nome da estratégia para logs."""

    def is_available(self) -> bool:
        """Verifica se a estratégia está disponível (configurada)."""
        return True