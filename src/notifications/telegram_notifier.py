"""
Implementação de notificações via Telegram Bot API.

Inclui TelegramNotifier para envio real e NullNotifier para quando
as notificações estão desabilitadas.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .events import NotificationEvent
from .notifier import Notifier

logger = logging.getLogger(__name__)


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

    async def _send_message(self, message: str) -> bool:
        """Envia mensagem via HTTP para Telegram Bot API."""
        url = f"{self._base_url}/sendMessage"
        data = {
            "chat_id": self._chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        # Retry com backoff exponencial (máximo 3 tentativas)
        for attempt in range(3):
            try:
                async with aiohttp.ClientSession(timeout=self._timeout) as session:
                    async with session.post(url, json=data) as response:
                        if response.status == 200:
                            result = await response.json()
                            if result.get("ok"):
                                logger.debug("telegram_message_sent", attempt=attempt + 1)
                                return True
                            else:
                                logger.warning(
                                    f"telegram_api_error attempt={attempt + 1}: "
                                    f"{result.get('description', 'unknown')}"
                                )
                        else:
                            logger.warning(
                                f"telegram_http_error attempt={attempt + 1}: "
                                f"status={response.status}"
                            )

            except asyncio.TimeoutError:
                logger.warning(f"telegram_timeout attempt={attempt + 1}")
            except aiohttp.ClientError as exc:
                logger.warning(f"telegram_network_error attempt={attempt + 1}: {type(exc).__name__}")

            # Backoff exponencial: 1s, 2s, 4s
            if attempt < 2:
                await asyncio.sleep(2**attempt)

        return False


class NullNotifier(Notifier):
    """Notificador que não faz nada — usado quando notificações estão desabilitadas."""

    async def send(self, event: NotificationEvent, payload: Any) -> bool:
        """Sempre retorna True (sucesso) sem fazer nada."""
        logger.debug("null_notifier_ignored", event=event.value)
        return True
