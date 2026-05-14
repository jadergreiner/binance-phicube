"""Allowed List Validator - valida email contra lista de autorizados."""

from src.api.auth.validators.auth_validator import AuthValidator, ValidationResult
from src.config.settings import get_settings


class AllowedListValidator(AuthValidator):
    """Valida se o email está na lista de autorizados."""

    async def _validate(self, email: str) -> ValidationResult:
        """Verifica se o email está na lista de autorizados."""
        settings = get_settings()

        if not settings.auth_allowed_emails:
            # Lista vazia = todos permitidos
            return ValidationResult(valid=True)

        if email in settings.auth_allowed_emails:
            return ValidationResult(valid=True)

        return ValidationResult(
            valid=False,
            error="Email não autorizado",
        )