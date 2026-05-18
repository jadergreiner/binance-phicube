"""Emergency Fallback - Facade Pattern.

Facade para recovery quando conta Google fica inacessível.
Esconde complexidade do recovery atrás de interface simples.
"""

from dataclasses import dataclass

from passlib.context import CryptContext

from src.api.auth.jwt_handler import create_token
from src.api.auth.strategies.auth_strategy import AuthResult
from src.config.settings import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass
class FallbackLoginRequest:
    """Requisição de login fallback."""

    username: str
    password: str


class EmergencyFacade:
    """Facade para login de emergência."""

    async def login_with_fallback(
        self, username: str, password: str
    ) -> AuthResult:
        """Autentica usando credenciais de fallback."""
        settings = get_settings()

        # Verificar se fallback está configurado
        if not settings.auth_fallback_user or not settings.auth_fallback_password_hash:
            return AuthResult(
                success=False,
                error="Fallback não configurado",
            )

        # Validar credenciais
        if username != settings.auth_fallback_user:
            return AuthResult(
                success=False,
                error="Credenciais inválidas",
            )

        if not pwd_context.verify(password, settings.auth_fallback_password_hash):
            return AuthResult(
                success=False,
                error="Credenciais inválidas",
            )

        # Gerar JWT
        jwt_token = create_token(
            subject=f"{username}@fallback",
            auth_method="fallback",
        )

        # Log de auditoria (simplificado - em produção usar MongoDB)
        # TODO: Implementar auditoria em coleção dedicated

        return AuthResult(
            success=True,
            token=jwt_token,
            user=f"{username}@fallback",
            auth_method="fallback",
        )

    async def report_lost_access(self, user: str) -> None:
        """Reporta perda de acesso para investigação."""
        # TODO: Implementar notificação e logging
        pass


# Instância global
_emergency_facade: EmergencyFacade | None = None


def get_emergency_facade() -> EmergencyFacade:
    """Retorna instância global do facade de emergência."""
    global _emergency_facade
    if _emergency_facade is None:
        _emergency_facade = EmergencyFacade()
    return _emergency_facade