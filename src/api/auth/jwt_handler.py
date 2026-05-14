"""JWT token handling for authentication."""

from dataclasses import dataclass
from datetime import datetime, timedelta

import jwt

from src.config.settings import get_settings


@dataclass
class TokenPayload:
    """Payload do JWT token."""

    sub: str  # Email do usuário
    exp: datetime
    iat: datetime
    role: str = "user"
    auth_method: str = "google"


def create_token(
    subject: str,
    auth_method: str = "google",
    role: str = "user",
    expiry_hours: int | None = None,
) -> str:
    """Cria um JWT token."""
    settings = get_settings()
    expiry = expiry_hours or settings.jwt_expiry_hours

    now = datetime.utcnow()
    payload = {
        "sub": subject,
        "exp": now + timedelta(hours=expiry),
        "iat": now,
        "role": role,
        "auth_method": auth_method,
    }

    secret = settings.jwt_secret
    if not secret:
        raise ValueError("JWT_SECRET não configurado")

    return jwt.encode(payload, secret, algorithm="HS256")


def verify_token(token: str) -> TokenPayload:
    """Verifica e decodifica um JWT token."""
    settings = get_settings()
    secret = settings.jwt_secret

    if not secret:
        raise ValueError("JWT_SECRET não configurado")

    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return TokenPayload(
            sub=payload["sub"],
            exp=datetime.fromtimestamp(payload["exp"]),
            iat=datetime.fromtimestamp(payload["iat"]),
            role=payload.get("role", "user"),
            auth_method=payload.get("auth_method", "google"),
        )
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expirado")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Token inválido: {e}")