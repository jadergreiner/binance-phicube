"""Authenticator - seleciona estratégia de autenticação.

Implementa Strategy Pattern para trocar estratégias em runtime.
"""

from typing import Any

from src.api.auth.strategies.auth_strategy import AuthResult, AuthStrategy
from src.api.auth.strategies.dev_bypass_strategy import DevBypassStrategy
from src.api.auth.strategies.oauth_strategy import OAuthStrategy
from src.config.settings import get_settings


class Authenticator:
    """Seleciona estratégia de autenticação baseada na configuração."""

    def __init__(self):
        self._oauth_strategy = OAuthStrategy()
        self._dev_bypass_strategy = DevBypassStrategy()

    def get_strategy(self) -> AuthStrategy:
        """Retorna a estratégia de autenticação apropriada."""
        settings = get_settings()

        # Prioridade: dev bypass > OAuth
        if settings.auth_dev_bypass:
            return self._dev_bypass_strategy

        if self._oauth_strategy.is_available():
            return self._oauth_strategy

        # Fallback: se nenhuma estratégia disponível, usar dev bypass
        # (para permitir startup em ambiente sem config)
        return self._dev_bypass_strategy

    async def authenticate(self, request: Any) -> AuthResult:
        """Autentica usando a estratégia selecionada."""
        strategy = self.get_strategy()
        return await strategy.authenticate(request)

    def get_strategy_name(self) -> str:
        """Retorna nome da estratégia atual."""
        return self.get_strategy().get_strategy_name()


# Instância global
_authenticator: Authenticator | None = None


def get_authenticator() -> Authenticator:
    """Retorna instância global do autenticador."""
    global _authenticator
    if _authenticator is None:
        _authenticator = Authenticator()
    return _authenticator