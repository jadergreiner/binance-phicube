# SPEC_031 — Backup Automático MongoDB

**ID:** SPEC_031
**Título:** Backup Automático MongoDB
**Data:** 2026-05-10
**Status:** Rascunho
**Versão:** 1.0
**Dependências:** SPEC_007 (resiliência), SPEC_021 (validação operacional)
**PRD §:** Fase 2 — "Continuidade operacional"

---

## 1. Objetivo

Implementar backup automatizado do banco MongoDB com dump diário, rotação e verificação de integridade, garantindo que dados de trades, posições e configurações sejam recuperáveis em caso de falha.

---

## 2. Escopo

### Dentro do escopo
- Script `tools/backup_mongo.sh` para dump via `mongodump`
- Agendamento cron diário dentro do container (ou host)
- Roteação: manter últimos 7 backups, remover mais antigos
- Verificação de integridade pós-dump (`mongorestore --dry`)
- Notificação via Telegram se backup falhar
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

### 5.1 Script `tools/backup_mongo.sh`

```bash
#!/bin/bash
# Uso: BACKUP_DIR=./backups/mongo MONGO_URI="mongodb://..." ./tools/backup_mongo.sh

set -euo pipefail

TIMESTAMP=$(date +%Y-%m-%d)
BACKUP_FILE="${BACKUP_DIR}/phicube_${TIMESTAMP}.gz"

mongodump "${MONGO_URI}" --gzip --archive="${BACKUP_FILE}"

# Verificação
mongorestore "${MONGO_URI}" --gzip --archive="${BACKUP_FILE}" --dry-run > /dev/null 2>&1

# Rotação: manter últimos 7
ls -tp "${BACKUP_DIR}"/phicube_*.gz | tail -n +8 | xargs -r rm

echo "${TIMESTAMP}" > "${BACKUP_DIR}/.last_backup_timestamp"
echo "OK"
```

### 5.2 Agendamento (Docker)

No `docker-compose.yml`, serviço `phicube` (ou container dedicado):

```yaml
services:
  phicube-backup:
    image: mongo:7
    container_name: phicube-backup
    entrypoint: |
      sh -c "
        crontab -l 2>/dev/null | { cat; echo '0 3 * * * /scripts/backup_mongo.sh >> /var/log/backup.log 2>&1'; } | crontab -
        cron -f
      "
    volumes:
      - ./tools/backup_mongo.sh:/scripts/backup_mongo.sh:ro
      - ./backups:/backups
      - mongo-data:/data/db:ro
    environment:
      - MONGO_URI=mongodb://phicube-mongo:27017
      - BACKUP_DIR=/backups/mongo
    depends_on:
      - phicube-mongo
```

### 5.3 Notificação de falha

```
No bot (src/main.py):
  - Ao iniciar, verificar se backup existe (arquivo < 24h)
  - Se não, log WARNING "Nenhum backup nos últimos 24h"
```

No script, integração opcional com Telegram (chamada HTTP post).

---

## 6. Invariantes

| ID | Invariante |
|----|-----------|
| INV-031-01 | Backup nunca é feito enquanto o bot está executando trades (race condition evitada) — executar em horário sem trades |
| INV-031-02 | Arquivo de dump válido: `mongorestore --dry-run` passa |
| INV-031-03 | No mínimo 1 backup dos últimos 7 dias sempre disponível |

---

## 7. Testes

| ID | Descrição |
|----|-----------|
| TEST_031_01 | Script de backup executa `mongodump` com sucesso |
| TEST_031_02 | Verificação de integridade passa para dump válido |
| TEST_031_03 | Rotação: mais de 7 backups → 7 mantidos, resto deletado |
| TEST_031_04 | Script falha graciosamente se MongoDB offline |
| TEST_031_05 | Container backup inicia e agendamento cron ativo (verificar via `docker exec`) |

---

## 8. Arquivos

| Arquivo | Mudança |
|---------|---------|
| `tools/backup_mongo.sh` | Criado — script de backup + rotação |
| `docker-compose.yml` | Modificado — serviço `phicube-backup` |
| `docs/OPERATIONS.md` | Modificado — seção de restore |
| `.gitignore` | Modificado — ignorar `backups/` |

---

## 9. Definition of Done

- [ ] `tools/backup_mongo.sh` funcional (dump + verify + rotate)
- [ ] Container backup integrado ao docker-compose
- [ ] Backup executado e verificado manualmente
- [ ] Notificação de falha operacional (log WARNING)
- [ ] `docs/OPERATIONS.md` com procedimento de restore
- [ ] TEST_031_01 a 05 passando
