"""Google OAuth Provider implementation."""

import urllib.parse
from dataclasses import dataclass

import httpx

from src.api.auth.oauth_provider import OAuthProvider, OAuthToken, UserInfo
from src.config.settings import get_settings


@dataclass
class GoogleOAuthConfig:
    """Configuração do Google OAuth."""

    client_id: str
    client_secret: str
    redirect_uri: str
    authorization_base_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url: str = "https://oauth2.googleapis.com/token"
    userinfo_url: str = "https://www.googleapis.com/oauth2/v2/userinfo"
    scopes: tuple[str, ...] = ("openid", "email", "profile")


class GoogleOAuthProvider(OAuthProvider):
    """Provedor OAuth para Google."""

    def __init__(self, config: GoogleOAuthConfig):
        self._config = config
        self._client = httpx.AsyncClient()

    async def close(self):
        """Fecha o cliente HTTP."""
        await self._client.aclose()

    def get_provider_name(self) -> str:
        return "google"

    def get_authorization_url(self, state: str) -> str:
        """Retorna URL de autorização do Google."""
        params = {
            "client_id": self._config.client_id,
            "redirect_uri": self._config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self._config.scopes),
            "state": state,
            "access_type": "offline",  # Para obter refresh token
            "prompt": "consent",  # Forçar consentimento para refresh token
        }
        return f"{self._config.authorization_base_url}?{urllib.parse.urlencode(params)}"

    def exchange_code(self, code: str) -> OAuthToken:
        """Troca código por token de acesso."""
        # Sincrono para compatibilidade com FastAPI dependency
        import requests

        data = {
            "client_id": self._config.client_id,
            "client_secret": self._config.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self._config.redirect_uri,
        }

        response = requests.post(self._config.token_url, data=data)
        response.raise_for_status()
        token_data = response.json()

        return OAuthToken(
            access_token=token_data["access_token"],
            id_token=token_data.get("id_token"),
            expires_in=token_data.get("expires_in", 3600),
            token_type=token_data.get("token_type", "Bearer"),
            refresh_token=token_data.get("refresh_token"),
        )

    def get_user_info(self, token: OAuthToken) -> UserInfo:
        """Busca informações do usuário no Google."""
        # Sincrono para compatibilidade com FastAPI dependency
        import requests

        headers = {"Authorization": f"Bearer {token.access_token}"}
        response = requests.get(self._config.userinfo_url, headers=headers)
        response.raise_for_status()
        user_data = response.json()

        return UserInfo(
            email=user_data["email"],
            name=user_data.get("name"),
            picture=user_data.get("picture"),
            id=user_data.get("id"),
        )


def get_google_oauth_provider() -> GoogleOAuthProvider | None:
    """Factory para criar GoogleOAuthProvider baseado nas configurações."""
    settings = get_settings()

    if not settings.google_client_id or not settings.google_client_secret:
        return None

    config = GoogleOAuthConfig(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri or "",
    )

    return GoogleOAuthProvider(config)