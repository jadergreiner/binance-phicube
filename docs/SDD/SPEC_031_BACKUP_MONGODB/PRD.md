# PRD — Backup Automático MongoDB

**Documento:** Product Requirements Document
**Feature:** Backup Automático MongoDB — Dump Diário, Rotação e Verificação de Integridade
**SPEC vinculada:** `SPEC_031_BACKUP_MONGODB/SPEC.md` (v2.0)
**PRD raiz:** `PRD.md` § Fase 2 — "Continuidade operacional"
**Data:** 2026-05-12
**Versão:** 1.0
**Status:** Concluído

---

## 1. Sumário Executivo

O bot registra **cada trade, sinal e evento de auditoria** no MongoDB. Esse histórico é a base para relatórios de performance, análise de conformidade com o método e verificação pós-operação. **Hoje não existe backup automatizado** — se o volume do MongoDB for corrompido, deletado acidentalmente ou o container falhar, todo o histórico de trades se perde.

**Backup Automático MongoDB resolve isso com dump diário, rotação e verificação:**

| Mecanismo | Descrição | Valor |
|-----------|-----------|-------|
| **Dump diário** | `mongodump` com gzip às 03:00 UTC via background task no próprio bot | Dados protegidos sem custo operacional extra (zero containers novos) |
| **Verificação de integridade** | `mongorestore --dry-run` pós-dump garante que o backup é válido | Restauração confiável — sem surpresas na hora da recuperação |
| **Rotação automática** | Últimos 7 backups mantidos; mais antigos removidos | Disco controlado — nunca acumula além de 7 dias |
| **Alerta de falha** | Notificação via Telegram se o dump ou verificação falhar | Operador sabe imediatamente que os dados estão desprotegidos |
| **Restore documentado** | Procedimento passo a passo em `docs/OPERATIONS.md` | Qualquer pessoa consegue restaurar em minutos |

---

## 2. Problema que Resolve

| Problema | Impacto Hoje | Como Backup Automático Resolve |
|----------|-------------|-------------------------------|
| **Perda total do histórico** | MongoDB corrompido ou volume deletado → zero dados de trades, sinais, auditoria. Sem possibilidade de calcular performance, declarar resultados ou auditar conformidade. | Backup diário com verificação de integridade. Perda máxima = 24h de dados. |
| **Sem procedimento de restore** | Se o banco cair, o operador precisa descobrir como restaurar — sem documentação, sem backup recente, sem confiança no arquivo. | `docs/OPERATIONS.md` com 3 variações de restore (local, Docker, específico). Backup pré-verificado. |
| **Custo operacional de backup manual** | Operador precisa parar o bot, executar `mongodump` manualmente, lembrar de refazer amanhã. Não escala. | Automático. O operador só descobre que o backup existe quando precisar restaurar. |
| **Falso senso de segurança** | "MongoDB é durável" — sim, mas volume Docker pode ser deletado com `docker compose down -v`. Ou um `dropDatabase` acidental. | A verdadeira proteção é um arquivo .gz fora do volume do MongoDB. |
| **Disco lotado de backups manuais** | Sem rotação, cada dump manual ocupa espaço — operador nunca limpa. | Rotação automática: sempre 7 backups, nunca mais. |

### Cenário Ilustrativo

| Situação | Hoje | Com Backup Automático |
|----------|------|----------------------|
| `docker compose down -v` acidental | Perda total — MongoDB resetado, zero trades recuperáveis | Restaura o dump mais recente, perde no máximo 24h |
| Corrupção do arquivo WiredTiger | Perda total — MongoDB não sobe, zero dados | Backup do dia anterior (verificado) restaura tudo |
| Operador quer migrar de servidor | Precisa parar, documentar, executar dump manual, copiar, restaurar — horas de trabalho | Backup já existe no diretório `./backups/mongo/`. Só copiar e restaurar. |
| "Preciso ver um trade de 3 semanas atrás" | Trade fechado há 3 semanas já pode ter sido perdido em rotação de logs | Backup diário cobre 7 dias contínuos. Para além disso, SPEC futura de S3/extensão. |

---

## 3. Valor para o Operador

1. **Perda máxima de 24h de dados:** backup diário com verificação cobre o pior caso. Dados de trades abertos persistem na exchange.
2. **Zero esforço operacional:** o bot faz backup sozinho. O operador não precisa lembrar, configurar cron, ou gerenciar scripts.
3. **Backup confiável:** verificação pós-dump com `mongorestore --dry-run` garante que o arquivo não está corrompido antes de rotacionar o anterior.
4. **Notificação proativa:** se algo falhar, o Telegram avisa imediatamente — não na próxima vez que o operador olhar o painel.
5. **Restore documentado e testável:** o procedimento está em `docs/OPERATIONS.md` com comandos copiáveis — qualquer pessoa consegue restaurar.
6. **CLI disponível:**`  phicube ops backup` para execução manual sob demanda (antes de migração, por exemplo).

---

## 4. Personas Impactadas

### Operador (primário)
- **Necessidade:** Saber que os dados de trades, sinais e auditoria estão protegidos e recuperáveis
- **Ganha:** Tranquilidade — se algo der errado com o MongoDB, o operador restaura o backup e continua
- **Perde se não fizermos:** Risco real de perda total do histórico operacional. Sem backup, não há como auditar trades antigos, calcular performance acumulada ou provar conformidade com o método

### Desenvolvedor (secundário)
- **Necessidade:** Mecanismo simples, zero infraestrutura adicional, testável em CI
- **Ganha:** `MongoBackup` é uma classe Python pura com injeção de dependência — testável com mocks sem MongoDB real. Usa `@retry`, `structlog` e `Notifier` ABC, todos padrões já existentes
- **Perde se não fizermos:** Precisaria manter script bash separado, cron container, integração manual com notificação — mais complexidade, menos testabilidade

---

## 5. Critérios de Sucesso

| Critério | Métrica | Alvo | Como Verificar |
|----------|---------|------|----------------|
| **Dump executado com sucesso** | `mongodump` retorna código 0 | 100% das execuções | TEST_031_05 |
| **Verificação de integridade passa** | `mongorestore --dry-run` retorna 0 | 100% dos backups válidos | TEST_031_06 |
| **Rotação correta** | Máximo 7 backups no diretório | Sempre ≤ 7 | TEST_031_02 |
| **Notificação de falha** | Telegram enviado se dump ou verify falhar | 100% das falhas notificadas | TEST_031_03 |
| **CLI funcional** | `phicube ops backup --dry-run` executa sem erro | 100% dos modos CLI | TEST_031_04 |
| **Verificação pós-startup** | Bot loga WARNING se backup desatualizado (>24h) | Toda inicialização | TEST_031_07 |
| **Restore documentado** | `docs/OPERATIONS.md` contém procedimento | Publicado | Leitura do documento |
| **Backup imutável** | `BackupRecord` é `@dataclass(frozen=True)` | Garantido por teste | TEST_031_01 |

---

## 6. Decisões de Produto

### Tomadas no refinamento

| Decisão | Opção Escolhida | Alternativa Rejeitada | Motivo |
|---------|----------------|----------------------|--------|
| **Linguagem do script** | Python (`tools/backup_mongo.py`) | Bash (`tools/backup_mongo.sh`) | Projeto é 100% Python. Bash não pode usar `@retry`, `Notifier` ABC, `structlog` nem `pytest`. |
| **Agendamento** | Background task `asyncio` no `main.py` | Container separado com cron | Cron dentro de container é anti-pattern Docker. O bot já tem processo asyncio longo — adicionar `BackupTask` é zero custo operacional. |
| **Notificação de falha** | `Notifier` ABC (Strategy Pattern) | HTTP POST direto para Telegram | Projeto já tem `TelegramNotifier` e `NullNotifier`. Reusar o ABC é consistente e testável. |
| **Verificação pós-dump** | `mongorestore --dry-run` obrigatório (opt-out via `--no-verify`) | Sem verificação | Dump corrompido só descoberto na hora do restore = perda de dados. Melhor saber na hora. |
| **Horário do backup** | 03:00 UTC (fixo) | Configurável pelo operador | Backup é operacional, não estratégico. 03:00 UTC é horário de baixa volatilidade. Configuração adicional seria ruído. |
| **Proteção contra sobrescrita** | `--force` necessário para sobrescrever dump do mesmo dia | Sobrescrita silenciosa | Dump de hoje com 10 minutos de diferença pode ter dados diferentes. Melhor forçar decisão consciente. |
| **Segurança em logs** | `_extract_host()` mostra apenas hostname, sem credenciais | Logar URI completa | URI MongoDB contém usuário e senha. Logar hostname apenas segue INV-031-05. |

### Em aberto

| Decisão | Responsável | Prazo |
|---------|-------------|-------|
| Backup para armazenamento externo (S3, SFTP) | SPEC futura | Pós-MVP |
| Notificação de sucesso de backup | Operador decide se quer | Pós-rollout inicial |
| Backup incremental vs. full | SPEC futura — sem necessidade imediata | Pós-MVP |

---

## 7. Conformidade com o Manifesto

| Princípio | Como SPEC_031 atende |
|-----------|---------------------|
| 1. Disciplina | Backup executado automaticamente todos os dias no mesmo horário. Zero decisão manual. |
| 2. Gestão de risco | Dados protegidos contra perda acidental. Perda máxima = 24h. |
| 3. Transparência | Cada execução de backup é logada com tamanho, verificação e duração. Falhas são notificadas. |
| 4. Configurabilidade | `mongodb_uri` e `backup_dir` configuráveis via `.env`. CLI para execução manual. |
| 5. Segurança | URI MongoDB nunca aparece em logs (apenas hostname). Notifier reusa infraestrutura existente. |
| 6. Resiliência | `@retry` no dump com backoff exponencial. Falha de backup não interrompe o bot. |
| 7. Evolução baseada em dados | Backup preserva o dado que alimenta relatórios de performance (SPEC_006), auditoria e análise. |

---

## 8. Risco e Rollout

### Estratégia de rollout

1. **Implementação única (já concluída):**
   - Testes unitários (TEST_031_01 a 08 — 19 testes, todos passando)
   - `ruff check` sem erros
   - 729/729 testes da suite passando, 0 regressão
   - Container Docker com volume `./backups:/app/backups`

2. **Ativação:**
   - `docker compose up -d` já monta o volume
   - Backup começa automaticamente à 03:00 UTC do primeiro dia
   - Operador pode testar imediatamente com `phicube ops backup`

3. **Pós-rollout:**
   - Verificar logs do bot na primeira execução agendada
   - Confirmar que `./backups/mongo/phicube_<data>.gz` foi criado
   - Testar restore em ambiente isolado

### Riscos conhecidos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| `mongodump` não instalado no container | Média (imagem `python:3.11-slim`) | Alto — backup não executa | Dockerfile precisa instalar `mongodb-database-tools`. Já documentado. |
| Disco cheio durante dump | Baixa (backup gzip é compacto) | Médio — dump falha | Rotação mantém só 7 backups. WARNING logado se falhar. |
| Backup do dia sobrescrito por execução manual | Baixa | Baixo — perde dados do dia anterior | `--force` necessário para sobrescrever. |
| Container reinicia exatamente às 03:00 | Muito baixa | Mínimo — backup do dia é perdido | Próximo ciclo tenta novamente em 24h. Operador pode executar manualmente. |

---

## 9. Fora de Escopo (v1)

- **Backup para S3/GDrive/SFTP:** o dump fica no disco local. Storage externo será SPEC futura.
- **Backup incremental:** apenas full dump. Dados do MongoDB são pequenos (< 100 MB para uso pessoal).
- **PITR (Point-in-Time Recovery):** requer oplog contínuo. Inviável para MVP.
- **Notificação de sucesso:** apenas falha é notificada. Sucesso é silencioso (apenas log).
- **Dashboard de status de backup:** sem UI — status via logs e CLI.
- **Criptografia do backup:** dados ficam em disco local sem criptografia adicional (proteção via permissão de arquivo).

---

## 10. Conexão com PRD Principal

Este PRD_031 é uma **especificação de feature** que complementa o [`PRD.md`](../../PRD.md) principal:

- **PRD.md § Fase 2 (Continuidade operacional):** backup automatizado é o primeiro item de continuidade implementado
- **PRD.md § Riscos (MongoDB indisponível):** risco existente mitigado — se MongoDB cair, o backup permite restore rápido com perda máxima de 24h
- **PRD.md § MVP item 4 (Storage Layer):** a resiliência do storage layer agora inclui backup externalizado
- **PRD.md SPEC_031 referenciada:** seção de riscos atualizada com status "Mitigado por SPEC_031"

### Atualizações recomendadas no PRD Principal

| O quê | Onde |
|------|------|
| Risco "MongoDB indisponível" atualizar status | PRD.md § Riscos |
| Item "Backup automatizado" adicionado à Fase 2 | PRD.md § Fase 2 |
| Versão incrementar | PRD.md — sugerido v1.3 |
| Histórico atualizar | PRD.md — linha `1.3 | 2026-05-12 | Time A | SPEC_031` |

---

## 11. Histórico

| Versão | Data | Autor | Mudanças |
|--------|------|-------|----------|
| 1.0 | 2026-05-12 | Time A (Refinamento) | Documento inicial pós-implementação e convergência SPEC_031 |
