"""OAuth Strategy implementation."""

import secrets
from typing import Any

from src.api.auth.jwt_handler import create_token
from src.api.auth.providers.google_oauth import get_google_oauth_provider
from src.api.auth.strategies.auth_strategy import AuthResult, AuthStrategy
from src.config.settings import get_settings


class OAuthStrategy(AuthStrategy):
    """Estratégia de autenticação via OAuth Google."""

    def get_strategy_name(self) -> str:
        return "oauth"

    def is_available(self) -> bool:
        """Verifica se OAuth está configurado."""
        settings = get_settings()
        return bool(
            settings.google_client_id
            and settings.google_client_secret
            and settings.google_redirect_uri
        )

    async def authenticate(self, request: Any) -> AuthResult:
        """Autentica via OAuth Google."""
        settings = get_settings()

        # Verificar se OAuth está configurado
        if not self.is_available():
            return AuthResult(
                success=False,
                error="OAuth não configurado",
            )

        # Obter provider
        provider = get_google_oauth_provider()
        if not provider:
            return AuthResult(
                success=False,
                error="Provider OAuth não disponível",
            )

        # Obter parâmetros da query
        code = request.query_params.get("code")
        state = request.query_params.get("state")

        if not code:
            # Retornar URL de autorização para redirect
            state = secrets.token_urlsafe(32)
            auth_url = provider.get_authorization_url(state)
            return AuthResult(
                success=False,
                error="redirect",
                user=auth_url,  # Usar campo user para retornar URL
            )

        # Validar state (simplificado - em produção usar sessão)
        if not state:
            return AuthResult(
                success=False,
                error="State inválido",
            )

        try:
            # Trocar código por token
            oauth_token = provider.exchange_code(code)

            # Buscar informações do usuário
            user_info = provider.get_user_info(oauth_token)

            # Verificar se email está na lista de autorizados
            if settings.auth_allowed_emails:
                if user_info.email not in settings.auth_allowed_emails:
                    return AuthResult(
                        success=False,
                        error="Email não autorizado",
                    )

            # Gerar JWT interno
            jwt_token = create_token(
                subject=user_info.email,
                auth_method="google",
            )

            return AuthResult(
                success=True,
                token=jwt_token,
                user=user_info.email,
                auth_method="google",
            )

        except Exception as e:
            return AuthResult(
                success=False,
                error=f"Erro na autenticação OAuth: {e}",
            )