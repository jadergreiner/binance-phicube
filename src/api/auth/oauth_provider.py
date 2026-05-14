"""OAuth Provider abstraction - Adapter Pattern.

Interface abstrata para provedores OAuth. Permite trocar provedores
(Google, GitHub, etc) sem modificar o código do handler.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class OAuthToken:
    """Token retornado pelo provedor OAuth."""

    access_token: str
    id_token: str | None = None
    expires_in: int = 3600
    token_type: str = "Bearer"
    refresh_token: str | None = None


@dataclass
class UserInfo:
    """Informações do usuário retornadas pelo provedor OAuth."""

    email: str
    name: str | None = None
    picture: str | None = None
    id: str | None = None


class OAuthProvider(ABC):
    """Interface abstrata para provedores OAuth."""

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Retorna URL de autorização para redirecionar o usuário."""

    @abstractmethod
    def exchange_code(self, code: str) -> OAuthToken:
        """Troca código de autorização por token."""

    @abstractmethod
    def get_user_info(self, token: OAuthToken) -> UserInfo:
        """Busca informações do usuário com o token de acesso."""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Retorna nome do provedor para logs."""