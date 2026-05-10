"""
Implementação de notificações via Telegram Bot API.

Inclui TelegramNotifier para envio real e NullNotifier para quando
as notificações estão desabilitadas.
"""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from src.common.decorators import retry
from src.monitoring.logger import get_logger

from .events import NotificationEvent
from .notifier import Notifier

logger = get_logger(__name__)


class TelegramApiError(Exception):
    """Exceção levantada quando a API do Telegram retorna erro não-200 ou ok=False."""

    pass


class TelegramNotifier(Notifier):
    """Notificador que envia mensagens via Telegram Bot API."""

    def __init__(self, token: str, chat_id: str) -> None:
        self._token = token
        self._chat_id = chat_id
        self._base_url = f"https://api.telegram.org/bot{token}"
        self._timeout = aiohttp.ClientTimeout(total=5.0)

    async def send(self, event: NotificationEvent, payload: Any) -> bool:
        """
        Envia notificação via Telegram.

        Implementa retry com backoff exponencial em caso de falha temporária.
        """
        try:
            message = self._format_message(event, payload)
            return await self._send_message(message)
        except Exception as exc:
            logger.warning(f"telegram_notification_failed: {event.value} - {type(exc).__name__}")
            return False

    def _format_message(self, event: NotificationEvent, payload: Any) -> str:
        """Formata o payload do evento em mensagem Telegram."""
        if hasattr(payload, "to_message"):
            return payload.to_message()

        # Fallback para eventos não estruturados
        return f"**{event.value.upper()}**\n\n{payload}"

    @retry(
        max_attempts=3,
        initial_delay=1.0,
        backoff_factor=2.0,
        exc_types=(asyncio.TimeoutError, aiohttp.ClientError, TelegramApiError),
        log_event_prefix="telegram_send",
    )
    async def _send_message(self, message: str) -> bool:
        """Envia mensagem via HTTP para Telegram Bot API.

        Usa @retry decorator com backoff exponencial (1s, 2s, 4s).
        Levanta exceção após 3 tentativas falhas (capturada por send()).
        """
        url = f"{self._base_url}/sendMessage"
        data = {
            "chat_id": self._chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("ok"):
                        logger.debug("telegram_message_sent")
                        return True
                    else:
                        description = result.get("description", "unknown")
                        logger.warning(f"telegram_api_error: {description}")
                        raise TelegramApiError(f"API returned ok=False: {description}")
                else:
                    logger.warning(f"telegram_http_error: status={response.status}")
                    raise TelegramApiError(f"HTTP status {response.status}")


class NullNotifier(Notifier):
    """Notificador que não faz nada — usado quando notificações estão desabilitadas."""

    async def send(self, event: NotificationEvent, payload: Any) -> bool:
        """Sempre retorna True (sucesso) sem fazer nada."""
        logger.debug("null_notifier_ignored", event_value=event.value)
        return True
