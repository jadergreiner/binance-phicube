"""
Módulo de notificações — envio de alertas operacionais via Telegram.

Este módulo implementa notificações assíncronas para eventos críticos do bot:
- Trade aberto com sucesso
- Erro crítico na execução
- Falha de proteção (SL não executado após entrada)

As notificações são opcionais e não bloqueiam o funcionamento do bot.
"""
from __future__ import annotations

from .events import NotificationEvent, SLMissingEvent
from .notifier import Notifier
from .telegram_notifier import NullNotifier, TelegramNotifier

__all__ = ["NotificationEvent", "Notifier", "TelegramNotifier", "NullNotifier", "SLMissingEvent"]
