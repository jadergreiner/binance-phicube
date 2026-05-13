"""Testes para OrderPipeline."""

from __future__ import annotations

import pytest

from src.trading.commands.base import Command
from src.trading.commands.pipeline import OrderPipeline, PipelineError


class FakeCommand(Command):
    """Command fake para testes."""

    def __init__(self, name: str, should_fail: bool = False) -> None:
        super().__init__()
        self._name = name
        self._should_fail = should_fail
        self.undo_called = False

    async def execute(self) -> dict:
        if self._should_fail:
            raise Exception(f"{self._name} failed")
        return {"name": self._name, "status": "ok"}

    async def undo(self) -> None:
        self.undo_called = True


class TestOrderPipeline:
    async def test_execute_all_success(self):
        pipeline = OrderPipeline()
        cmd1 = FakeCommand("cmd1")
        cmd2 = FakeCommand("cmd2")

        pipeline.add(cmd1).add(cmd2)
        result = await pipeline.execute()

        assert result.ok is True
        assert result.success is True
        assert len(result.commands_executed) == 2
        assert "FakeCommand" in result.commands_executed
        assert len(result.results) == 2

    async def test_execute_rollback_on_failure(self):
        pipeline = OrderPipeline()
        cmd1 = FakeCommand("cmd1")
        cmd2 = FakeCommand("cmd2")
        cmd3 = FakeCommand("cmd3", should_fail=True)

        pipeline.add(cmd1).add(cmd2).add(cmd3)

        with pytest.raises(PipelineError) as exc_info:
            await pipeline.execute()

        error = exc_info.value  # noqa: F841
        assert "cmd3 failed" in str(error)
        assert error.failed_command == "FakeCommand"
        assert cmd1.undo_called is True
        assert cmd2.undo_called is True
        assert cmd3.undo_called is False  # Não chegou a executar

    async def test_execute_first_failure(self):
        pipeline = OrderPipeline()
        cmd1 = FakeCommand("cmd1", should_fail=True)
        cmd2 = FakeCommand("cmd2")

        pipeline.add(cmd1).add(cmd2)

        with pytest.raises(PipelineError):
            await pipeline.execute()

        assert cmd1.undo_called is False  # Falhou, não precisa undo
        assert cmd2.undo_called is False  # Não chegou a executar

    async def test_history_tracks_all_commands(self):
        pipeline = OrderPipeline()
        cmd1 = FakeCommand("cmd1")
        cmd2 = FakeCommand("cmd2")

        pipeline.add(cmd1).add(cmd2)
        await pipeline.execute()

        history = pipeline.history
        assert len(history) == 2
        assert history[0]["command"] == "FakeCommand"
        assert history[0]["status"] == "success"
        assert history[1]["status"] == "success"

    async def test_history_tracks_failure_and_rollback(self):
        pipeline = OrderPipeline()
        cmd1 = FakeCommand("cmd1")
        cmd2 = FakeCommand("cmd2", should_fail=True)

        pipeline.add(cmd1).add(cmd2)

        with pytest.raises(PipelineError):
            await pipeline.execute()

        history = pipeline.history
        assert len(history) == 3  # success + failed + undo
        assert history[0]["status"] == "success"
        assert history[1]["status"] == "failed"
        assert history[2]["status"] == "undone"

    async def test_empty_pipeline(self):
        pipeline = OrderPipeline()
        result = await pipeline.execute()

        assert result.ok is True
        assert len(result.commands_executed) == 0
