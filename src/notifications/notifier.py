"""
Contrato base para notificadores — interface comum para envio de notificações.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .events import NotificationEvent


class Notifier(ABC):
    """Interface base para sistemas de notificação."""

    @abstractmethod
    async def send(self, event: NotificationEvent, payload: Any) -> bool:
        """
        Envia uma notificação para o evento especificado.

        Args:
            event: Tipo do evento de notificação
            payload: Dados específicos do evento (TradeOpenedEvent, etc.)

        Returns:
            True se a notificação foi enviada com sucesso, False caso contrário

        Note:
            Esta operação NÃO deve lançar exceções — deve retornar False em caso de falha.
            O objetivo é que falhas de notificação nunca interrompam o fluxo principal do bot.
        """
        pass
