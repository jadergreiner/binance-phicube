"""Command base para operações de ordem."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Command(ABC):
    """Base class para comandos de ordem com suporte a undo."""

    def __init__(self) -> None:
        self._executed = False
        self._result: dict[str, Any] | None = None
        self._error: Exception | None = None

    @abstractmethod
    async def execute(self) -> dict[str, Any]:
        """Executa o comando e retorna o resultado da ordem."""

    @abstractmethod
    async def undo(self) -> None:
        """Reverte o comando executado."""

    @property
    def executed(self) -> bool:
        return self._executed

    @property
    def result(self) -> dict[str, Any] | None:
        return self._result

    @property
    def error(self) -> Exception | None:
        return self._error

    def _mark_executed(self, result: dict[str, Any]) -> dict[str, Any]:
        self._executed = True
        self._result = result
        return result

    def _mark_failed(self, error: Exception) -> None:
        self._error = error
        self._executed = False
