"""Pipeline para orquestrar comandos de ordem com rollback automático."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.monitoring.logger import get_logger
from src.trading.commands.base import Command

logger = get_logger(__name__)


@dataclass
class PipelineResult:
    """Resultado da execução do pipeline."""

    success: bool
    commands_executed: list[str] = field(default_factory=list)
    commands_failed: list[str] = field(default_factory=list)
    results: list[dict[str, Any]] = field(default_factory=list)
    error: Exception | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def ok(self) -> bool:
        return self.success and self.error is None


class PipelineError(Exception):
    """Erro lançado quando o pipeline falha e rollback é acionado."""

    def __init__(
        self,
        message: str,
        failed_command: str,
        executed_commands: list[str],
        original_error: Exception,
    ) -> None:
        super().__init__(message)
        self.failed_command = failed_command
        self.executed_commands = executed_commands
        self.original_error = original_error


class OrderPipeline:
    """Orquestra comandos de ordem e executa rollback em cascata em caso de falha."""

    def __init__(self) -> None:
        self._commands: list[Command] = []
        self._history: list[dict[str, Any]] = []

    def add(self, command: Command) -> OrderPipeline:
        """Adiciona um comando ao pipeline."""
        self._commands.append(command)
        return self

    async def execute(self) -> PipelineResult:
        """Executa todos os comandos em sequência.

        Em caso de falha, chama undo() de todos os comandos já executados
        em ordem reversa.
        """
        result = PipelineResult(success=True)
        executed: list[Command] = []

        for command in self._commands:
            command_name = type(command).__name__
            try:
                cmd_result = await command.execute()
                executed.append(command)
                result.commands_executed.append(command_name)
                result.results.append(cmd_result)
                self._history.append(
                    {
                        "command": command_name,
                        "status": "success",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "result": cmd_result,
                    }
                )
                logger.info(
                    "pipeline_command_executed",
                    command=command_name,
                )
            except Exception as exc:
                result.success = False
                result.commands_failed.append(command_name)
                result.error = exc
                self._history.append(
                    {
                        "command": command_name,
                        "status": "failed",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "error": type(exc).__name__,
                    }
                )
                logger.error(
                    "pipeline_command_failed",
                    command=command_name,
                    error_type=type(exc).__name__,
                    action="rollback_started",
                )

                # Rollback: undo em ordem reversa
                await self._rollback(executed)

                raise PipelineError(
                    message=f"Pipeline failed at {command_name}: {exc}",
                    failed_command=command_name,
                    executed_commands=result.commands_executed,
                    original_error=exc,
                ) from exc

        logger.info(
            "pipeline_completed",
            commands_executed=len(result.commands_executed),
        )
        return result

    async def _rollback(self, executed: list[Command]) -> None:
        """Executa undo de todos os comandos em ordem reversa."""
        for command in reversed(executed):
            command_name = type(command).__name__
            try:
                await command.undo()
                self._history.append(
                    {
                        "command": command_name,
                        "status": "undone",
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                )
                logger.info(
                    "pipeline_command_undone",
                    command=command_name,
                )
            except Exception as exc:
                self._history.append(
                    {
                        "command": command_name,
                        "status": "undo_failed",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "error": type(exc).__name__,
                    }
                )
                logger.error(
                    "pipeline_undo_failed",
                    command=command_name,
                    error_type=type(exc).__name__,
                )
                # Não relança — tenta undo dos demais comandos

    @property
    def history(self) -> list[dict[str, Any]]:
        """Retorna o histórico de execução do pipeline."""
        return self._history.copy()
