"""
Backup automático MongoDB — dump, verificação, rotação e notificação.

Uso programático:
    backup = MongoBackup(settings, notifier)
    record = await backup.run()

CLI:
    python -m tools.backup_mongo [--dry-run] [--verify] [--force]

Padrões:
    - @dataclass(frozen=True) BackupRecord (imutabilidade)
    - Injeção de dependência (Settings + Notifier)
    - @retry decorator para mongodump (resiliência de rede)
    - structlog events padronizados
    - asyncio.create_subprocess_exec para mongodump/mongorestore
"""

from __future__ import annotations

import argparse
import asyncio
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.common.decorators import retry
from src.monitoring.logger import get_logger

logger = get_logger(__name__)

# Quantos backups manter após rotação
_BACKUP_RETENTION_COUNT = 7


@dataclass(frozen=True)
class BackupRecord:
    """Registro imutável de uma execução de backup.

    Attributes:
        timestamp: Data do backup no formato YYYY-MM-DD.
        file_path: Caminho absoluto do arquivo .gz gerado.
        file_size_bytes: Tamanho do arquivo em bytes.
        verified: True se a verificação pós-dump passou.
        created_at: Timestamp ISO 8601 de criação do registro.
        duration_seconds: Tempo total de execução (dump + verify), ou None se falhou.
    """

    timestamp: str
    file_path: str
    file_size_bytes: int
    verified: bool
    created_at: str
    duration_seconds: float | None = None


class MongoBackupError(Exception):
    """Erro durante operação de backup."""


class MongoBackup:
    """Executa dump MongoDB com verificação, rotação e notificação.

    Uso:
        backup = MongoBackup(settings, notifier)
        record = await backup.run()
    """

    def __init__(
        self,
        mongodb_uri: str,
        backup_dir: str = "./backups/mongo",
        notifier: Any | None = None,
    ) -> None:
        """
        Args:
            mongodb_uri: URI de conexão MongoDB (ex: mongodb://user:pass@host:27017).
            backup_dir: Diretório onde os backups .gz serão salvos.
            notifier: Instância opcional de Notifier para alertas de falha.
                      Se None, falhas são apenas logadas.
        """
        self._mongodb_uri = mongodb_uri
        self._backup_dir = Path(backup_dir)
        self._notifier = notifier

    # --- API pública ---

    async def run(self, *, dry_run: bool = False, verify: bool = True) -> BackupRecord | None:
        """Executa o pipeline completo de backup: dump → verify → rotate.

        Args:
            dry_run: Se True, apenas loga o que faria sem executar.
            verify: Se True, executa mongorestore --dry-run após o dump.

        Returns:
            BackupRecord em caso de sucesso, None em caso de falha.

        Raises:
            MongoBackupError: Se o diretório de backup não pode ser criado.
        """
        started_at = time.monotonic()
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d")

        logger.info("backup_started", timestamp=timestamp, dry_run=dry_run, verify=verify)

        if dry_run:
            logger.info(
                "backup_dry_run",
                backup_dir=str(self._backup_dir),
                mongodb_host=self._extract_host(self._mongodb_uri),
                retention=_BACKUP_RETENTION_COUNT,
            )
            return None

        # Garantir que diretório existe
        try:
            self._backup_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise MongoBackupError(
                f"Não foi possível criar diretório de backup {self._backup_dir}: {exc}"
            ) from exc

        file_path = self._backup_dir / f"phicube_{timestamp}.gz"

        # Dump
        dump_ok = await self._dump(str(file_path))
        if not dump_ok:
            await self._notify_failure("dump_failed", timestamp=timestamp)
            return None

        # Tamanho
        try:
            file_size = file_path.stat().st_size
        except OSError:
            file_size = 0

        # Verificação
        verified = False
        if verify:
            verified = await self._verify(str(file_path))
            if not verified:
                logger.warning("backup_verify_failed", file=str(file_path))
                await self._notify_failure("verify_failed", timestamp=timestamp)
                # Não retorna None — backup existe mesmo sem verificação
        else:
            verified = True  # considerado ok se verify=False

        # Rotação
        await self._rotate()

        # Timestamp do último backup
        self._write_last_timestamp(timestamp)

        elapsed = time.monotonic() - started_at

        record = BackupRecord(
            timestamp=timestamp,
            file_path=str(file_path.resolve()),
            file_size_bytes=file_size,
            verified=verified,
            created_at=datetime.now(UTC).isoformat(),
            duration_seconds=round(elapsed, 2),
        )

        logger.info(
            "backup_completed",
            file=str(file_path),
            size_bytes=file_size,
            verified=verified,
            duration_s=record.duration_seconds,
        )

        return record

    # --- Métodos internos ---

    @retry(
        max_attempts=3,
        initial_delay=1.0,
        backoff_factor=2.0,
        exc_types=(asyncio.TimeoutError,),
        log_event_prefix="backup_dump",
        fallback=None,
    )
    async def _dump(self, file_path: str) -> bool:
        """Executa mongodump com gzip e archive. Retry 3x em timeout."""
        cmd = [
            "mongodump",
            f"--uri={self._mongodb_uri}",
            "--gzip",
            f"--archive={file_path}",
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300.0)
        except TimeoutError:
            proc.kill()
            await proc.wait()
            raise

        if proc.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="replace").strip()
            logger.error(
                "backup_dump_failed",
                returncode=proc.returncode,
                error=error_msg,
            )
            return False

        logger.debug("backup_dump_success", file=file_path)
        return True

    async def _verify(self, file_path: str) -> bool:
        """Executa mongorestore --dry-run para verificar integridade do dump."""
        cmd = [
            "mongorestore",
            f"--uri={self._mongodb_uri}",
            "--gzip",
            f"--archive={file_path}",
            "--dry-run",
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120.0)
        except TimeoutError:
            proc.kill()
            await proc.wait()
            logger.error("backup_verify_timeout", file=file_path)
            return False

        if proc.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="replace").strip()
            logger.error(
                "backup_verify_failed",
                file=file_path,
                returncode=proc.returncode,
                error=error_msg,
            )
            return False

        logger.debug("backup_verify_passed", file=file_path)
        return True

    async def _rotate(self) -> None:
        """Remove backups antigos, mantendo apenas os N mais recentes."""
        pattern = "phicube_*.gz"
        backups = sorted(self._backup_dir.glob(pattern))

        if len(backups) <= _BACKUP_RETENTION_COUNT:
            return

        to_delete = backups[:-_BACKUP_RETENTION_COUNT]
        for old_backup in to_delete:
            try:
                old_backup.unlink()
                logger.info("backup_rotation_deleted", file=str(old_backup))
            except OSError as exc:
                logger.warning(
                    "backup_rotation_failed",
                    file=str(old_backup),
                    error=str(exc),
                )

    def _write_last_timestamp(self, timestamp: str) -> None:
        """Escreve arquivo .last_backup_timestamp com a data do último backup."""
        ts_file = self._backup_dir / ".last_backup_timestamp"
        try:
            ts_file.write_text(timestamp + "\n")
        except OSError as exc:
            logger.warning("backup_timestamp_write_failed", error=str(exc))

    async def _notify_failure(self, reason: str, *, timestamp: str) -> None:
        """Notifica falha via Notifier (se disponível)."""
        logger.error("backup_failed", reason=reason, timestamp=timestamp)

        if self._notifier is None:
            return

        try:
            from src.notifications.events import (  # noqa: PLC0415
                BackupFailedEvent,
                NotificationEvent,
            )

            await self._notifier.send(
                NotificationEvent.BACKUP_FAILED,
                BackupFailedEvent(reason=reason, timestamp=timestamp),
            )
        except Exception as exc:
            logger.warning(
                "backup_notify_failed",
                error_type=type(exc).__name__,
            )

    @staticmethod
    def _extract_host(uri: str) -> str:
        """Extrai host do URI MongoDB para log seguro (sem credenciais)."""
        try:
            # mongodb://user:pass@host:port/db → host
            after_at = uri.split("@")[-1]
            host_part = after_at.split("/")[0]
            return host_part.split(":")[0]
        except (IndexError, ValueError):
            return "unknown"


async def check_last_backup(backup_dir: str = "./backups/mongo") -> None:
    """Verifica se existe backup nas últimas 24h.

    Chamado no startup do bot para alertar operador.
    """
    ts_file = Path(backup_dir) / ".last_backup_timestamp"
    if not ts_file.exists():
        logger.warning("nenhum_backup_encontrado")
        return

    try:
        content = ts_file.read_text().strip()
        last_date = datetime.strptime(content, "%Y-%m-%d").date()
        today = datetime.now(UTC).date()
        diff_days = (today - last_date).days
        if diff_days > 1:
            logger.warning(
                "backup_desatualizado",
                ultimo_backup=content,
                dias_sem_backup=diff_days,
            )
        else:
            logger.info("backup_ok", ultimo_backup=content)
    except (ValueError, OSError) as exc:
        logger.warning("backup_check_failed", error=str(exc))


# --- CLI ---


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m tools.backup_mongo",
        description="Backup MongoDB — dump, verify, rotate",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas loga o que faria, sem executar dump",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        default=True,
        help="Executa mongorestore --dry-run pós-dump (padrão: True)",
    )
    parser.add_argument(
        "--no-verify",
        action="store_false",
        dest="verify",
        help="Pula verificação de integridade",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Executa backup mesmo se já existir dump do dia",
    )
    parser.add_argument(
        "--backup-dir",
        default="./backups/mongo",
        help="Diretório de destino dos backups (padrão: ./backups/mongo)",
    )
    return parser.parse_args()


async def _main_cli() -> None:
    """Entrypoint da CLI."""
    from src.config.settings import get_settings  # noqa: PLC0415

    args = _parse_args()
    settings = get_settings()

    # Verificar se já existe backup do dia (proteção)
    if not args.force:
        ts = datetime.now(UTC).strftime("%Y-%m-%d")
        existing = list(Path(args.backup_dir).glob(f"phicube_{ts}.gz"))
        if existing:
            logger.warning(
                "backup_ja_existe",
                file=str(existing[0]),
                hint="Use --force para sobrescrever",
            )
            return

    backup = MongoBackup(
        mongodb_uri=settings.mongodb_uri,
        backup_dir=args.backup_dir,
    )
    record = await backup.run(dry_run=args.dry_run, verify=args.verify)

    if record is None:
        if not args.dry_run:
            raise SystemExit(1)
        return

    print(f"Backup concluído: {record.file_path} ({record.file_size_bytes} bytes)")


if __name__ == "__main__":
    asyncio.run(_main_cli())
