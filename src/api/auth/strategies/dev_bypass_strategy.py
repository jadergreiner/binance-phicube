"""Dev Bypass Strategy implementation.

Estratégia de autenticação para desenvolvimento local.
Permite login simples sem OAuth Google.
"""

from typing import Any

from passlib.context import CryptContext

from src.api.auth.jwt_handler import create_token
from src.api.auth.strategies.auth_strategy import AuthResult, AuthStrategy
from src.config.settings import get_settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class DevBypassStrategy(AuthStrategy):
    """Estratégia de autenticação para desenvolvimento."""

    def get_strategy_name(self) -> str:
        return "dev_bypass"

    def is_available(self) -> bool:
        """Verifica se dev bypass está habilitado."""
        settings = get_settings()
        return settings.auth_dev_bypass

    async def authenticate(self, request: Any) -> AuthResult:
        """Autentica via dev bypass (usuário fixo para desenvolvimento)."""
        settings = get_settings()

        if not settings.auth_dev_bypass:
            return AuthResult(
                success=False,
                error="Dev bypass desabilitado",
            )

        # Em modo dev, criar token para usuário fixo
        # Não requer credenciais - apenas confirma que bypass está ativo
        jwt_token = create_token(
            subject="dev@localhost",
            auth_method="dev_bypass",
        )

        return AuthResult(
            success=True,
            token=jwt_token,
            user="dev@localhost",
            auth_method="dev_bypass",
        )