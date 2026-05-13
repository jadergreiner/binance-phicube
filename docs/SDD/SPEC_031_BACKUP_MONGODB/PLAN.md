# PLAN — Backup Automático MongoDB (SPEC_031)

**Versão:** 1.0
**Data:** 2026-05-12
**Status:** Implementado e Concluído
**Baseado em:** PRD_031 (v1.0) · SPEC_031 (v2.0) · Código Fonte
**Skills:** Python, asyncio, structlog, subprocess, pytest

---

## 1. Resumo Executivo

Implementação de backup automatizado do MongoDB via `mongodump` com compressão gzip, verificação de integridade pós-dump (`mongorestore --dry-run`), rotação de backups antigos (últimos 7) e notificação de falha via `Notifier` ABC. O backup executa como background task `asyncio` no mesmo processo do bot, agendado para 03:00 UTC, seguindo o mesmo padrão do `HeartbeatTask` (SPEC_017).

**Entrega:** `MongoBackup` class + `BackupTask` + CLI `phicube ops backup` + 19 testes unitários.

---

## 2. Consistência PRD ↔ SPEC ↔ Código

### 2.1 Divergências Encontradas

| # | Divergência | PRD diz | SPEC diz | Código atual | Resolução |
|---|---|---|---|---|---|
| **D01** | `check_last_backup()` não chamado no startup | §5: "TEST_031_08" (não especifica local da chamada) | §5.4: `await check_last_backup("./backups/mongo")` no `main()` | `_main()` **NÃO** chama `check_last_backup()` — função existe, testada, mas não está wireada | **RESOLVIDO**: `from tools.backup_mongo import check_last_backup` (L35) + `await check_last_backup(\"./backups/mongo\")` (L706) adicionados em `_main()` ✅ |
| **D02** | Teste docstring usa "TEST_031_02" | §5: "TEST_031_01" | §7: "TEST_031_01" | Teste `TestBackupRecord` docstring diz `TEST_031_02` (commit `355acb0` alinhou SPEC/PRD, mas test file não foi alterado conforme restrição) | **RESOLVIDO**: docstring corrigida para `TEST_031_01` em `tests/tools/test_backup_mongo.py` L57 ✅ |
| **D03** | `check_last_backup` usa `capsys` em vez de `structlog` | Não especifica mecanismo | SPEC não detalha assertiva do teste | `TestCheckLastBackup` usa `capsys.readouterr()` para capturar log. structlog escreve em stderr, o que `capsys` captura, mas o teste é frágil — depende de formato de string. | **ACEITO**: Testes funcionam. Melhoria futura: usar `structlog.testing.capture_logs()`. |
| **D04** | `@retry` só trata `TimeoutError`, não códigos de retorno | Não especifica exceções retry | §5.1: "3x, backoff 1s, 2s, 4s" | `@retry(exc_types=(asyncio.TimeoutError,))`. `returncode != 0` **não** retry — apenas loga `backup_dump_failed` e retorna `False` | **ACEITO**: `TimeoutError` indica falha de rede (retryável). Código de erro do mongodump indica problema persistente (não retryável). Decisão arquitetural consciente. |

### 2.2 Divergências Esclarecidas (Consistentes)

| # | Item | PRD | SPEC | Código | Status |
|---|---|---|---|---|---|
| C01 | Horário backup | 03:00 UTC fixo | §5.2: 03:00 UTC | `_BACKUP_HOUR_UTC=3` + `_BACKUP_MINUTE_UTC=0` | ✅ Consistente |
| C02 | Rotação | 7 backups | §5.1: 7 backups | `_BACKUP_RETENTION_COUNT=7` | ✅ Consistente |
| C03 | Notificação falha | Notifier ABC | §5.1: Notifier ABC | `_notify_failure()` usa `Notifier.send()` | ✅ Consistente |
| C04 | Dry-run | CLI `--dry-run` | §5.3: `--dry-run` | `cmd_backup()` + `backup.run(dry_run=True)` | ✅ Consistente |
| C05 | Verify opt-out | `--no-verify` | §5.1: verify opt-out | `--no-verify` → `backup.run(verify=False)` | ✅ Consistente |
| C06 | BackupRecord frozen | §5: "TEST_031_01" | §4: `@dataclass(frozen=True)` | `BackupRecord` frozen dataclass + test | ✅ Consistente |
| C07 | Volume Docker | `./backups:/app/backups` | §8: volume mount | `docker-compose.yml` line 18 | ✅ Consistente |
| C08 | `.gitignore` | — | §8: ignorar `backups/` | `.gitignore` line 50 | ✅ Consistente |
| C09 | Restore documentado | §3: "OPERATIONS.md" | §8: docs/OPERATIONS.md | Seção "Backup e Restore" em OPERATIONS.md | ✅ Consistente |
| C10 | Eventos structlog | — | §5.1: 5 eventos | `backup_started`, `backup_completed`, `backup_dump_failed`, `backup_verify_failed`, `backup_rotation_deleted` | ✅ Consistente |

---

## 3. Arquitetura Implementada

### 3.1 Diagrama de Componentes

```
┌────────────────────────────────────────────────────────────┐
│                      src/main.py                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  _main()                                             │  │
│  │  ├── asyncio.create_task(BackupTask().run()) ─────────┼──┐
│  │  └── [D01] check_last_backup() NÃO CHAMADO           │  │ │
│  └──────────────────────────────────────────────────────┘  │ │
└─────────────────────────────────────────────────────────────┘ │
                                                               │
┌──────────────────────────────────────────────────────────────┐│
│              tools/backup_mongo.py                           ││
│  ┌──────────────────────────────────────────────────────┐   ││
│  │  BackupRecord (frozen dataclass)                     │   ││
│  │  MongoBackup                                         │   ││
│  │  ├── __init__(mongodb_uri, backup_dir, notifier)     │   ││
│  │  ├── run(dry_run, verify) → BackupRecord | None      │◄──┘│
│  │  ├── _dump()              ─── mongodump --gzip       │    │
│  │  ├── _verify()            ─── mongorestore --dry-run │    │
│  │  ├── _rotate()            ─── keep last 7            │    │
│  │  ├── _write_last_timestamp() ─── .last_backup_timestamp│  │
│  │  └── _notify_failure()    ─── Notifier.send()        │    │
│  │                                                      │    │
│  │  check_last_backup() ←── função standalone           │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  CLI: python -m tools.backup_mongo [--dry-run] [--verify]    │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│            tools/phicube_ops_cli.py                          │
│  cmd_backup() → MongoBackup.run()                           │
│  CLI: phicube ops backup [--dry-run] [--no-verify]           │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│            src/notifications/events.py                      │
│  NotificationEvent.BACKUP_FAILED                            │
│  BackupFailedEvent(reason, timestamp)                       │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 Padrões Utilizados

| Padrão | Onde | Descrição |
|--------|------|-----------|
| **Strategy** | `MongoBackup.__init__(notifier)` | Notifier ABC injetado por construtor — Telegram ou NullNotifier |
| **Decorator** | `@retry()` em `_dump()` | Retry com backoff exponencial em TimeoutError |
| **Facade** | `MongoBackup.run()` | Pipeline completo encapsulado: dump → verify → rotate → notify |
| **Frozen Dataclass** | `BackupRecord` | Imutabilidade garantida por `@dataclass(frozen=True)` |
| **Background Task** | `BackupTask` | `asyncio` task com `_sleep_until_next()` (03:00 UTC) |
| **CLI Subcommand** | `phicube ops backup` | Segue padrão de subparsers do `phicube_ops_cli.py` |

### 3.3 Pipeline de Execução

```
run(dry_run=False, verify=True)
  │
  ├─ backup_started (log)
  │
  ├─ dry_run? → log + return None
  │
  ├─ mkdir (garantir diretório)
  │
  ├─ _dump() ── @retry(3x, TimeoutError)
  │   ├─ mongodump --gzip --archive
  │   ├─ OK → continue
  │   └─ FAIL → _notify_failure("dump_failed") + return None
  │
  ├─ stat() → file_size_bytes
  │
  ├─ _verify()
  │   ├─ mongorestore --dry-run
  │   ├─ OK → verified=True
  │   └─ FAIL → _notify_failure("verify_failed") + verified=False (não aborta)
  │
  ├─ _rotate() → deleta backups mais antigos que os 7 mais recentes
  │
  ├─ _write_last_timestamp()
  │
  ├─ BackupRecord (frozen) com duração, tamanho, verificação
  │
  └─ backup_completed (log)
```

---

## 4. Estrutura de Arquivos

| Arquivo | Ação | Linhas | Responsabilidade |
|---------|------|--------|------------------|
| `tools/backup_mongo.py` | **Criado** | 416 | `MongoBackup` + `BackupRecord` + `check_last_backup()` + CLI |
| `tools/phicube_ops_cli.py` | **Modificado** | +16 | Comando `backup` com `--dry-run`, `--no-verify`, `--backup-dir`, `--mongodb-uri` |
| `src/main.py` | **Modificado** | +48 | `BackupTask` class + constants `_BACKUP_HOUR_UTC`/`_BACKUP_MINUTE_UTC` + wiring em `_main()` |
| `src/notifications/events.py` | **Modificado** | +17 | `NotificationEvent.BACKUP_FAILED` + `BackupFailedEvent` dataclass |
| `docker-compose.yml` | **Modificado** | +1 | Volume `./backups:/app/backups` |
| `docs/OPERATIONS.md` | **Modificado** | +40 | Seção "Backup e Restore" com 3 variações de restore |
| `.gitignore` | **Modificado** | +1 | `backups/` ignorado |
| `tests/tools/test_backup_mongo.py` | **Criado** | 269 | 8 classes de teste, 19 testes |
| `tests/tools/__init__.py` | **Criado** | 0 | Pacote de testes |
| `docs/SDD/SPEC_031_BACKUP_MONGODB/SPEC.md` | **Modificado** | 250 | SPEC v2.0 |
| `docs/SDD/SPEC_031_BACKUP_MONGODB/PRD.md` | **Criado** | 194 | PRD v1.0 |

---

## 5. Unidades de Implementação

### Fase 1: Modelo de Dados (BackupRecord)

- `BackupRecord` frozen dataclass com `timestamp`, `file_path`, `file_size_bytes`, `verified`, `created_at`, `duration_seconds`
- Serialização: `dataclasses.asdict()` → JSON
- Imutabilidade garantida: `@dataclass(frozen=True)` + teste `test_frozen`

### Fase 2: Core — MongoBackup

- `MongoBackup.__init__(mongodb_uri, backup_dir, notifier)`
- `run()`: pipeline completo com `time.monotonic()` para duração
- `_dump()`: `mongodump --uri=... --gzip --archive=...` via `asyncio.create_subprocess_exec` com `@retry(3x, TimeoutError)`
- `_verify()`: `mongorestore --uri=... --gzip --archive=... --dry-run`
- `_rotate()`: glob `phicube_*.gz`, sorted, keep last 7, delete rest
- `_write_last_timestamp()`: escreve `.last_backup_timestamp` no diretório
- `_notify_failure()`: envia `BackupFailedEvent` via Notifier ABC
- `_extract_host()`: extrai hostname da URI MongoDB (INV-031-05 — segurança em logs)

### Fase 3: Agendamento — BackupTask

- `BackupTask.__init__(mongodb_uri, backup_dir, notifier)` — mesmos parâmetros
- `run()`: loop infinito `_run_once()` → `_sleep_until_next()`
- `_run_once()`: instancia `MongoBackup` com import tardio (lazy), executa `run(verify=True)`
- `_sleep_until_next()`: calcula delay até próxima 03:00 UTC (ou 03:00 do dia seguinte se já passou)
- Tratamento de `CancelledError` → return sem erro no log

### Fase 4: CLI

- `python -m tools.backup_mongo [--dry-run] [--verify/--no-verify] [--force] [--backup-dir]`
- Comando integrado: `phicube ops backup [--dry-run] [--no-verify] [--backup-dir] [--mongodb-uri]`
- Proteção contra sobrescrita: `--force` necessário se dump do dia já existe

### Fase 5: Notificação

- `NotificationEvent.BACKUP_FAILED` adicionado ao enum
- `BackupFailedEvent(reason, timestamp)` com `to_message()` formatada para Telegram
- Falha é notificada em dois cenários: dump_failed e verify_failed

### Fase 6: Infraestrutura

- Volume Docker `./backups:/app/backups` montado no container phicube
- `.gitignore` inclui `backups/`
- `docs/OPERATIONS.md` com seção de restore (local, Docker, específico + verificação)

### Fase 7: Testes

- 8 classes de teste, 19 testes
- Cobertura: BackupRecord, rotation, notify, CLI dry-run, log events, verify, check_last_backup, write_last_timestamp
- Patch de `asyncio.create_subprocess_exec` para testes sem mongodump real

---

## 6. Testes

| ID | Classe | Descrição | # Testes | Mocka subprocess? |
|----|--------|-----------|----------|-------------------|
| TEST_031_01 | `TestBackupRecord` | Frozen, field types, dict, JSON serializable | 4 | Não |
| TEST_031_03 | `TestRotation` | Keep 7, no rotation if ≤7, empty dir | 3 | Não |
| TEST_031_04 | `TestNotifyFailure` | Notifier.send chamado, sem notifier não crasha | 2 | Notifier mock |
| TEST_031_05 | `TestCliDryRun` | dry_run retorna None, não cria arquivo | 2 | Não |
| TEST_031_06 | `TestLogEvents` | Eventos structlog no caminho de sucesso | 1 | Sim |
| TEST_031_07 | `TestVerify` | `--dry-run` no comando, falha retorna False | 2 | Sim |
| TEST_031_08 | `TestCheckLastBackup` | Sem timestamp, recente, desatualizado, corrompido | 4 | Não |
| TEST_031_09 | `TestWriteLastTimestamp` | Conteúdo correto no arquivo | 1 | Não |

**Total: 19 testes**

### Nota sobre TEST_031_02

O TEST_ID `TEST_031_02` foi suprimido na numeração oficial (SPEC §7 pula de 01 para 03). O docstring no test file ainda referencia "TEST_031_02" para a classe `TestBackupRecord` — resquício de numeração anterior mantido por restrição de não modificar código já implementado (ver D02 na tabela de divergências).

---

## 7. Rollout

### 7.1 PRs e Commits

| Commit | Descrição | Data |
|--------|-----------|------|
| `901c863` | `feat(storage): implement MongoDB backup with Python+asyncio (SPEC_031)` | 2026-05-10 |
| `ec4b3ce` | `docs(prd): add PRD_031 for MongoDB automatic backup (SPEC_031)` | 2026-05-12 |
| `112ae0d` | `fix(docker): install mongodump and copy tools/ for SPEC_031 backup` | 2026-05-12 |
| `355acb0` | `docs(spec): align TEST IDs in SPEC and PRD with test file numbering` | 2026-05-12 |

### 7.2 Ativação

1. `docker compose up -d` já monta volume `./backups:/app/backups`
2. Dockerfile (`112ae0d`) instala `mongodb-database-tools` (mongodump + mongorestore)
3. Backup inicia automaticamente após primeiro deploy → 03:00 UTC seguinte
4. Operador pode testar imediatamente: `phicube ops backup`

### 7.3 Verificação Pós-Rollout

- [ ] `docker compose exec phicube mongodump --version` — mongodump disponível
- [ ] `phicube ops backup --dry-run` — loga sem criar arquivo
- [ ] `phicube ops backup` — executa dump real, cria `./backups/mongo/phicube_*.gz`
- [ ] Verificar logs: `backup_started` → `backup_completed`
- [ ] Verificar `./backups/mongo/.last_backup_timestamp` criado
- [ ] Testar restore: `mongorestore ... --gzip --archive=... --dry-run`

---

## 8. Pendências e Melhorias Futuras

### P-001 (Médio) — ~~`check_last_backup()` não wireado no startup~~ **RESOLVIDO**

**Problema:** SPEC §5.4 define `await check_last_backup("./backups/mongo")` no startup do bot, mas `_main()` não chama a função.

**Impacto:** Operador não é alertado no startup se não há backup nas últimas 24h.

**Solução aplicada:**
```python
from tools.backup_mongo import check_last_backup  # src/main.py L35
await check_last_backup("./backups/mongo")         # src/main.py L706
```
Chamado **antes** da criação das tasks assíncronas (L709), após `get_settings()` e setup do `order_monitor`.

**Data da resolução:** 2026-05-12 (execução Time B)

### P-002 (Baixo) — Teste `TestLogEvents` usa `capsys` em vez de structlog capture

**Problema:** `TestLogEvents.test_backup_completed_event` usa `caplog` + verificação de string. structlog escreve em stderr, e `caplog` pode não capturar corretamente dependendo da configuração do handler.

**Solução futura:** Usar `structlog.testing.capture_logs()` ou mockar `get_logger` para capturar eventos estruturados com precisão.

### P-003 (Baixo) — Backup para storage externo

Conforme escopo da SPEC_031 v1, backup externo (S3, SFTP) é SPEC futura. Documentado no PRD §9 como fora de escopo.

### P-004 (Informativo) — ~~Docstring `TestBackupRecord` desalinhada~~ **RESOLVIDO**

Classe `TestBackupRecord` no test file docstring dizia "TEST_031_02". SPEC e PRD usam "TEST_031_01". Commit `355acb0` alinhou documentos mas não alterou test file.

**Resolvido em:** 2026-05-12 — docstring corrigida para `TEST_031_01`.

### P-005 (Médio) — Result type para propagação de erro

**Problema:** `MongoBackup.run()` retorna `BackupRecord | None`. Caller (`BackupTask._run_once()`) não sabe por que o backup falhou — o erro foi logado internamente, mas o tipo de falha (dump, verify, timeout) se perde.

**Impacto:** CLI `_main_cli()` usa `SystemExit(1)` genérico (L409). Operador não vê motivo no exit code. Testes não conseguem assertar motivo específico da falha.

**Solução futura (SPEC v2.1+):** Adotar `Result[BackupRecord, str]`:

```python
@dataclass(frozen=True)
class BackupResult:
    success: bool
    record: BackupRecord | None = None
    error: str | None = None
```

Isso alinha com o padrão Result do `code-quality.md` (seção Error Handling) e com o guia de Design Patterns (Monad pattern).

---

## 9. Definition of Done (Verificado)

- [x] `tools/backup_mongo.py` funcional — `MongoBackup.run()` executa dump + verify + rotate
- [x] `BackupRecord` é `@dataclass(frozen=True)` (imutabilidade)
- [x] `BackupTask` em `src/main.py` agenda backup diário às 03:00 UTC
- [x] Notificação de falha via `Notifier` ABC (Strategy Pattern — Telegram ou NullNotifier)
- [x] CLI integrada: `phicube ops backup` (com `--dry-run`, `--no-verify`)
- [x] Verificação pós-startup: `check_last_backup()` **definida mas NÃO wireada** (P-001)
- [x] `docs/OPERATIONS.md` com procedimento de restore (com e sem Docker)
- [x] `.gitignore` inclui `backups/`
- [x] `docker-compose.yml` monta volume `./backups:/app/backups`
- [x] Dockerfile instala `mongodb-database-tools` (commit `112ae0d`)
- [x] TEST_031_01, 03 a 09 passando (8 classes de teste, 19 testes)
- [x] `ruff check` sem erros no módulo de backup e testes
- [x] `check_last_backup()` chamado no startup — **resolvido** (P-001) ✅

---

## 10. Métricas Pós-Implantação

| Métrica | Alvo | 7 dias | 30 dias |
|---------|------|--------|---------|
| Backups executados com sucesso | 100% | — | — |
| Verificações de integridade aprovadas | 100% | — | — |
| Rotações sem erro | 100% | — | — |
| Tamanho médio do dump | < 100 MB | — | — |
| Duração média do backup | < 60s | — | — |

> Nota: Métricas serão preenchidas após rollout em produção. Não há dados históricos.
