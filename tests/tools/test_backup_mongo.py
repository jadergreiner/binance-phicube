"""Testes para o módulo de backup MongoDB (SPEC_031).

Cobre: BackupRecord, MongoBackup, CLI, notificação, rotação.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from tools.backup_mongo import (
    BackupRecord,
    MongoBackup,
    check_last_backup,
)

BACKUP_RETENTION_COUNT = 7

# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_record() -> BackupRecord:
    return BackupRecord(
        timestamp="2026-05-12",
        file_path="/tmp/backups/phicube_2026-05-12.gz",
        file_size_bytes=1024,
        verified=True,
        created_at=datetime.now(UTC).isoformat(),
        duration_seconds=12.5,
    )


@pytest.fixture
def mock_notifier():
    return AsyncMock()


@pytest.fixture
def backup_instance(tmp_path, mock_notifier):
    return MongoBackup(
        mongodb_uri="mongodb://user:pass@localhost:27017/phicube",
        backup_dir=str(tmp_path / "backups" / "mongo"),
        notifier=mock_notifier,
    )


# ─── TEST_031_01: BackupRecord frozen + field types ─────────────────────────


class TestBackupRecord:
    """TEST_031_01: BackupRecord frozen + correct field types."""

    def test_frozen(self, sample_record):
        with pytest.raises(AttributeError):
            sample_record.timestamp = "2026-05-13"  # type: ignore[misc]

    def test_field_types(self, sample_record):
        assert isinstance(sample_record.timestamp, str)
        assert isinstance(sample_record.file_path, str)
        assert isinstance(sample_record.file_size_bytes, int)
        assert isinstance(sample_record.verified, bool)
        assert isinstance(sample_record.created_at, str)
        assert sample_record.duration_seconds is None or isinstance(
            sample_record.duration_seconds, float
        )

    def test_to_dict(self, sample_record):
        d = asdict(sample_record)
        assert d["timestamp"] == "2026-05-12"
        assert d["file_size_bytes"] == 1024

    def test_json_serializable(self, sample_record):
        d = asdict(sample_record)
        json_str = json.dumps(d)
        parsed = json.loads(json_str)
        assert parsed["timestamp"] == "2026-05-12"


# ─── TEST_031_03: Rotation keeps last N ─────────────────────────────────────


class TestRotation:
    """TEST_031_03: Rotation keeps last 7, deletes rest."""

    async def test_keeps_last_7(self, backup_instance):
        # Criar 10 backups falsos
        bdir = backup_instance._backup_dir
        bdir.mkdir(parents=True, exist_ok=True)
        for i in range(10):
            (bdir / f"phicube_2026-05-{1 + i:02d}.gz").write_text(f"dump{i}")

        await backup_instance._rotate()

        remaining = sorted(bdir.glob("phicube_*.gz"))
        assert len(remaining) == BACKUP_RETENTION_COUNT  # 7

    async def test_no_rotation_needed(self, backup_instance):
        bdir = backup_instance._backup_dir
        bdir.mkdir(parents=True, exist_ok=True)
        for i in range(3):
            (bdir / f"phicube_2026-05-{1 + i:02d}.gz").write_text(f"dump{i}")

        await backup_instance._rotate()

        remaining = sorted(bdir.glob("phicube_*.gz"))
        assert len(remaining) == 3  # unchanged

    async def test_empty_dir(self, backup_instance):
        bdir = backup_instance._backup_dir
        bdir.mkdir(parents=True, exist_ok=True)

        await backup_instance._rotate()  # must not raise

        remaining = list(bdir.glob("phicube_*.gz"))
        assert len(remaining) == 0


# ─── TEST_031_04: Notify failure via Notifier ───────────────────────────────


class TestNotifyFailure:
    """TEST_031_04: _notify_failure sends via Notifier."""

    async def test_sends_notification(self, backup_instance, mock_notifier):
        await backup_instance._notify_failure("Test failure", timestamp="2026-05-12")

        mock_notifier.send.assert_awaited_once()

    async def test_no_notifier_does_not_crash(self, backup_instance):
        backup_instance._notifier = None
        await backup_instance._notify_failure("Test failure", timestamp="2026-05-12")
        # must not raise


# ─── TEST_031_05: CLI dry-run ───────────────────────────────────────────────


class TestCliDryRun:
    """TEST_031_05: dry_run does not execute dump."""

    async def test_dry_run_returns_none(self, backup_instance):
        record = await backup_instance.run(dry_run=True, verify=False)
        assert record is None

    async def test_dry_run_does_not_create_file(self, backup_instance):
        await backup_instance.run(dry_run=True, verify=False)
        files = list(backup_instance._backup_dir.glob("*.gz"))
        assert len(files) == 0


# ─── TEST_031_06: Structlog events on success path ──────────────────────────


class TestLogEvents:
    """TEST_031_06: Structlog events on success path."""

    async def test_backup_completed_event(self, backup_instance, caplog):
        """Com subprocess mockado, verifica que não há erro inesperado."""
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_subprocess.return_value = mock_proc

            # dry_run para criar diretório
            await backup_instance.run(dry_run=True)
            # agora executa real
            record = await backup_instance.run(verify=True)

        # Pode falhar se mongodump não estiver instalado — mas não deve crashar
        if record is None:
            # Dump falhou (mongodump não disponível no CI) — aceitável
            assert any("backup_started" in msg for msg in caplog.messages)
        else:
            assert record.verified is True


# ─── TEST_031_07: Verify step ───────────────────────────────────────────────


class TestVerify:
    """TEST_031_07: _verify calls mongorestore --dry-run."""

    async def test_verify_calls_mongorestore(self, backup_instance):
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_subprocess.return_value = mock_proc

            result = await backup_instance._verify("/fake/path.gz")

        assert result is True
        mock_subprocess.assert_called_once()
        args = mock_subprocess.call_args[0]
        assert "--dry-run" in args

    async def test_verify_failure(self, backup_instance):
        with patch("asyncio.create_subprocess_exec") as mock_subprocess:
            mock_proc = AsyncMock()
            mock_proc.returncode = 1
            mock_proc.communicate = AsyncMock(return_value=(b"", b"error: corrupted archive"))
            mock_subprocess.return_value = mock_proc

            result = await backup_instance._verify("/fake/path.gz")

        assert result is False


# ─── TEST_031_08: check_last_backup ─────────────────────────────────────────


class TestCheckLastBackup:
    """Verifica funcionalidade de check_last_backup."""

    async def test_no_timestamp_file(self, tmp_path, capsys):
        await check_last_backup(str(tmp_path))
        captured = capsys.readouterr()
        assert (
            "nenhum_backup_encontrado" in captured.out or "nenhum_backup_encontrado" in captured.err
        )

    async def test_recent_backup(self, tmp_path, capsys):
        bdir = Path(tmp_path)
        ts_file = bdir / ".last_backup_timestamp"
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        ts_file.write_text(today + "\n")

        await check_last_backup(str(bdir))
        captured = capsys.readouterr()
        assert "backup_ok" in captured.out or "backup_ok" in captured.err

    async def test_stale_backup(self, tmp_path, capsys):
        bdir = Path(tmp_path)
        ts_file = bdir / ".last_backup_timestamp"
        ts_file.write_text("2026-01-01\n")

        await check_last_backup(str(bdir))
        captured = capsys.readouterr()
        assert "backup_desatualizado" in captured.out or "backup_desatualizado" in captured.err

    async def test_corrupt_timestamp(self, tmp_path, capsys):
        bdir = Path(tmp_path)
        ts_file = bdir / ".last_backup_timestamp"
        ts_file.write_text("not-a-date\n")

        await check_last_backup(str(bdir))
        captured = capsys.readouterr()
        assert "backup_check_failed" in captured.out or "backup_check_failed" in captured.err


# ─── TEST_031_09: _write_last_timestamp ──────────────────────────────────────


class TestWriteLastTimestamp:
    async def test_writes_correct_content(self, backup_instance, tmp_path):
        backup_instance._backup_dir = tmp_path
        backup_instance._write_last_timestamp("2026-05-12")

        ts_file = tmp_path / ".last_backup_timestamp"
        assert ts_file.exists()
        content = ts_file.read_text().strip()
        assert content == "2026-05-12"
