# SPEC_031 — Backup Automático MongoDB

**ID:** SPEC_031
**Título:** Backup Automático MongoDB
**Data:** 2026-05-10
**Status:** Concluída
**Versão:** 2.0
**Dependências:** SPEC_007 (resiliência), SPEC_021 (validação operacional)
**PRD §:** Fase 2 — "Continuidade operacional"
**Skills requeridas:** Python, asyncio, structlog, subprocess, pytest

---

## 1. Objetivo

Implementar backup automatizado do banco MongoDB com dump diário, rotação e verificação de integridade, garantindo que dados de trades, posições e configurações sejam recuperáveis em caso de falha.

---

## 2. Escopo

### Dentro do escopo
- Módulo `tools/backup_mongo.py` com classe `MongoBackup` (dump via `mongodump`)
- Agendamento via `asyncio` background task em `src/main.py` (BackupTask)
- Roteação: manter últimos 7 backups, remover mais antigos
- Verificação de integridade pós-dump (`mongorestore --dry-run`)
- Notificação via `Notifier` ABC (Strategy Pattern) se backup falhar
- CLI integrada ao `phicube ops backup`
- Documentação de restore: `docs/OPERATIONS.md`

### Fora do escopo
- Backup para S3 / armazenamento externo (será SPEC futura)
- Backup incremental (só full dump)
- PITR (Point-in-Time Recovery)

---

## 3. User Stories

### US-031-01 — Backup diário automático
**Como** operador,
**quero** que o MongoDB seja dumpado automaticamente todo dia às 03:00,
**para** não perder dados em caso de desastre.

**Critério de aceite:**
- Dump salvo em `./backups/mongo/phicube_<YYYY-MM-DD>.gz`
- Últimos 7 backups mantidos
- Log de sucesso via structlog

### US-031-02 — Alerta de falha de backup
**Como** operador,
**quero** ser notificado no Telegram se o backup falhar,
**para** agir rapidamente.

**Critério de aceite:**
- Falha de `mongodump` → notificação enviada
- Falha de verificação de integridade → notificação enviada

---

## 4. Modelo de Dados

### `@dataclass(frozen=True) BackupRecord`

```python
@dataclass(frozen=True)
class BackupRecord:
    timestamp: str            # YYYY-MM-DD
    file_path: str            # Caminho absoluto do .gz
    file_size_bytes: int
    verified: bool            # True se mongorestore --dry-run passou
    created_at: str           # ISO 8601
    duration_seconds: float | None = None
```

### Estrutura de diretórios

```
backups/
  mongo/
    phicube_2026-05-10.gz         # dump de hoje
    phicube_2026-05-09.gz
    ...
    .last_backup_timestamp        # arquivo com timestamp do último backup bem-sucedido
```

---

## 5. Componentes

### 5.1 Classe `MongoBackup` (`tools/backup_mongo.py`)

Classe Python que encapsula dump, verificação, rotação e notificação.

```python
class MongoBackup:
    """Executa dump MongoDB com verificação, rotação e notificação.

    Uso:
        backup = MongoBackup(mongodb_uri, backup_dir, notifier)
        record = await backup.run()
    """

    def __init__(
        self,
        mongodb_uri: str,
        backup_dir: str = "./backups/mongo",
        notifier: Notifier | None = None,  # Strategy Pattern
    ) -> None: ...

    async def run(self, *, dry_run: bool = False, verify: bool = True) -> BackupRecord | None:
        """Pipeline: dump → verify → rotate → notificar se falha."""
```

**Pipeline interno (`run()`):**

| Passo | Método | Descrição |
|-------|--------|-----------|
| 1. Dump | `_dump()` | `mongodump --gzip --archive` via `asyncio.create_subprocess_exec()` com `@retry` decorator (3x, backoff 1s, 2s, 4s) |
| 2. Verify | `_verify()` | `mongorestore --dry-run` via subprocess |
| 3. Rotação | `_rotate()` | Mantém últimos 7 backups (`_BACKUP_RETENTION_COUNT = 7`) |
| 4. Timestamp | `_write_last_timestamp()` | Escreve `.last_backup_timestamp` |
| 5. Notificação | `_notify_failure()` | Envia `BackupFailedEvent` via `Notifier` ABC se dump ou verify falhar |

**Eventos structlog obrigatórios:**

```
logger.info("backup_started", timestamp, dry_run, verify)
logger.info("backup_completed", file, size_bytes, verified, duration_s)
logger.error("backup_dump_failed", returncode, error)
logger.warning("backup_verify_failed", file, returncode, error)
logger.info("backup_rotation_deleted", file)
```

### 5.2 Agendamento — `BackupTask` (`src/main.py`)

Background task `asyncio` executando no mesmo processo do bot (sem container separado).

```python
class BackupTask:
    """Executa backup MongoDB diário às 03:00 UTC.

    Padrão: mesma estrutura de HeartbeatTask (SPEC_017).
    Usa asyncio.sleep dinâmico para acordar na hora agendada.
    """

    async def run(self) -> None:
        while True:
            await self._run_once()
            await self._sleep_until_next()  # calcula delay até próxima 03:00 UTC

    async def _run_once(self) -> None:
        backup = MongoBackup(mongodb_uri, backup_dir, notifier)
        record = await backup.run(verify=True)
```

Startup em `main()`:

```python
backup_task = BackupTask(mongodb_uri=settings.mongodb_uri, notifier=notifier)
asyncio.create_task(backup_task.run())
```

### 5.3 CLI — `phicube ops backup`

Comando integrado ao CLI existente (`tools/phicube_ops_cli.py`):

```bash
phicube ops backup                    # executa backup
phicube ops backup --dry-run          # apenas loga o que faria
phicube ops backup --no-verify        # pula verificação
phicube ops backup --backup-dir ...   # diretório customizado
```

Ou via módulo:

```bash
python -m tools.backup_mongo
```

### 5.4 Verificação pós-startup

No `main()` do bot, ao iniciar:

```python
from tools.backup_mongo import check_last_backup
await check_last_backup("./backups/mongo")
```

Se não existe backup nas últimas 24h → log WARNING `backup_desatualizado`.

---

## 6. Invariantes

| ID | Invariante |
|----|-----------|
| INV-031-01 | `mongodump --gzip --archive` produz snapshot consistente do WiredTiger — execução simultânea com o bot é segura |
| INV-031-02 | Arquivo de dump válido: `mongorestore --dry-run` passa |
| INV-031-03 | No mínimo 1 backup dos últimos 7 dias sempre disponível |
| INV-031-04 | `BackupRecord` é imutável (`@dataclass(frozen=True)`) |
| INV-031-05 | Token ou credencial nunca aparece em logs de backup (usar `_extract_host()` para log seguro) |

---

## 7. Testes

| ID | Test Class | Descrição |
|----|-----------|-----------|
| TEST_031_01 | `TestBackupRecord` | `BackupRecord` frozen, field types, dict serialization, JSON serializable |
| TEST_031_02 | `TestRotation` | Rotação mantém últimos 7, não rotaciona se ≤7, não crasha em dir vazio |
| TEST_031_03 | `TestNotifyFailure` | `_notify_failure` envia via Notifier; sem notifier não crasha |
| TEST_031_04 | `TestCliDryRun` | dry_run retorna None, não cria arquivo |
| TEST_031_05 | `TestLogEvents` | Eventos structlog no caminho de sucesso |
| TEST_031_06 | `TestVerify` | `_verify` chama mongorestore --dry-run; falha retorna False |
| TEST_031_07 | `TestCheckLastBackup` | Sem timestamp, backup recente, backup desatualizado, timestamp corrompido |
| TEST_031_08 | `TestWriteLastTimestamp` | `_write_last_timestamp` escreve conteúdo correto |

---

## 8. Arquivos

| Arquivo | Mudança |
|---------|---------|
| `tools/backup_mongo.py` | Criado — `MongoBackup` + `BackupRecord` + CLI |
| `tools/phicube_ops_cli.py` | Modificado — comando `backup` adicionado |
| `src/main.py` | Modificado — `BackupTask` background + `check_last_backup` no startup |
| `src/notifications/events.py` | Modificado — `BACKUP_FAILED` event + `BackupFailedEvent` |
| `docker-compose.yml` | Modificado — volume `./backups:/app/backups` no serviço `phicube` |
| `docs/OPERATIONS.md` | Modificado — seção de restore |
| `docs/SDD/SPEC_031_BACKUP_MONGODB/SPEC.md` | Modificado — esta SPEC (v2.0) |
| `.gitignore` | Modificado — ignorar `backups/` |
| `tests/tools/test_backup_mongo.py` | Criado — 8 classes de teste (TEST_031_01 a 08) |
| `tests/tools/__init__.py` | Criado — pacote de testes |

---

## 9. Definition of Done

- [x] `tools/backup_mongo.py` funcional — `MongoBackup.run()` executa dump + verify + rotate
- [x] `BackupRecord` é `@dataclass(frozen=True)` (imutabilidade)
- [x] `BackupTask` em `src/main.py` agenda backup diário às 03:00 UTC via `asyncio`
- [x] Notificação de falha via `Notifier` ABC (Strategy Pattern — Telegram ou NullNotifier)
- [x] CLI integrada: `phicube ops backup` (com `--dry-run`, `--no-verify`)
- [x] Verificação pós-startup: `check_last_backup()` loga WARNING se backup desatualizado
- [x] `docs/OPERATIONS.md` com procedimento de restore (com e sem Docker)
- [x] `.gitignore` inclui `backups/`
- [x] `docker-compose.yml` monta volume `./backups:/app/backups` no serviço `phicube`
- [x] TEST_031_01 a 08 passando (8 classes de teste, 19 testes)
- [x] `ruff check` sem erros no módulo de backup e testes
