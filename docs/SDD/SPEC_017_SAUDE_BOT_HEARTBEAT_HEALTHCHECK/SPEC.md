# SPEC_017 — Saúde do Bot: Heartbeat no MongoDB e Healthcheck HTTP

**ID:** SPEC_017
**Status:** Concluída
**Data:** 2026-05-06
**Autor:** Time A (Refinamento)
**Executores:** Time B (Execução) — Backend Sênior + DevOps
**Skill de validação:** `sdd-spec-driven-development`, `qa-review`

---

## 1. Título e Resumo

### 1.1 Nome da Funcionalidade

Saúde do Bot — Heartbeat Periódico no MongoDB e Healthcheck HTTP para Docker

### 1.2 Resumo (High-Level Definition)

**O que é:** Dois mecanismos complementares de observabilidade do processo do bot
(`src/main.py`): (1) uma task assíncrona que grava um documento `heartbeat` na
collection `audit` a cada 5 minutos, permitindo que qualquer consumidor do MongoDB
saiba que o processo está vivo; (2) um servidor HTTP mínimo (asyncio puro, porta
8081 interna) que responde `200 OK` em `GET /health`, exclusivamente para uso do
Docker `healthcheck`. Adicionalmente, o campo `bot_process` do endpoint `GET /health`
da API do dashboard (atualmente `"unknown"`) passa a ser derivado do último heartbeat
registrado no MongoDB.

**Por que estamos fazendo:** O processo do bot e o processo da API do dashboard são
containers separados sem comunicação direta. O `GET /health` da API atualmente retorna
`"bot_process": "unknown"` — uma informação operacionalmente inútil. Se o bot travar
silenciosamente (sem exceção, sem log, sem ciclo), nenhum mecanismo atual detecta isso.
O operador só descobrirá quando perguntar por que nenhum trade foi aberto.

**Valor de negócio:** Elimina o blind spot operacional mais crítico do sistema: um bot
travado passa a ser detectável em até 10 minutos; o Docker restart automático pode ser
acionado; o operador vê `"bot_process": "dead"` no dashboard em vez de `"unknown"`.

**Conexão com PRD/SPEC:** PRD §Princípios — "operador sempre informado de situações
críticas"; SPEC_016 §5.1 `GET /health` — campo `bot_process` identificado como gap
em refinamento; SPEC_007 §5 — padrão de resiliência e observabilidade do projeto.

---

## 2. Objetivos e Escopo

### 2.1 Objetivos (o que será entregue)

- [ ] OBJ-01: Task `HeartbeatTask` em `src/main.py` grava heartbeat na collection `audit`
      a cada 5 minutos
- [ ] OBJ-02: Servidor HTTP mínimo em asyncio puro, porta 8081 interna, rota `GET /health`,
      rodando como task adicional em `_main()`
- [ ] OBJ-03: `docker-compose.yml` atualizado com `healthcheck` no serviço `phicube`
- [ ] OBJ-04: `GET /health` da API do dashboard atualizado: campo `bot_process` derivado
      do último heartbeat no MongoDB (não mais literal `"unknown"`)
- [ ] OBJ-05: Índice TTL na collection `audit` para documentos `event_type: "heartbeat"`
      com expiração de 24 horas

### 2.2 Fora do Escopo (Non-Goals)

- **Não inclui:** Healthcheck por `TradingMonitor` individual — detecta "processo vivo",
  não "todos os monitors saudáveis"
- **Não inclui:** Alertas via Telegram quando bot detectado como inativo — já coberto
  pela SPEC_016 (indicador visual) e SPEC_012 (alertas críticos)
- **Não inclui:** Métricas de performance do processo (CPU, memória) — fora do escopo
- **Não inclui:** Porta 8081 exposta externamente — endpoint é exclusivo para Docker daemon
- **Não inclui:** Substituição do mecanismo de `get_last_bot_activity_at()` existente —
  o heartbeat complementa, não substitui; a collection `audit` já é consultada pela SPEC_016

---

## 3. Referências

| Documento | Seção | Relevância |
|---|---|---|
| `src/main.py` | `_main()`, `TradingMonitor.run()` | Ponto de inserção da HeartbeatTask e do servidor HTTP |
| `src/api/routes/health.py` | `health_check()` | Campo `bot_process` a ser atualizado (OBJ-04) |
| `src/storage/repository.py` | `audit()`, `get_last_bot_activity_at()` | Contrato de gravação e leitura do heartbeat |
| `docker-compose.yml` | serviço `mongo` | Padrão de healthcheck a replicar para `phicube` |
| `SPEC_016/SPEC.md` | §5.1 `GET /health`, §5.2 `get_last_bot_activity_at()` | Gap `bot_process: "unknown"` que esta SPEC resolve |
| `SPEC_007/SPEC.md` | §5 | Padrão de resiliência: falha não-fatal não deve parar o processo principal |

---

## 4. Histórias de Usuário e Requisitos

### US-017-01: Heartbeat periódico do processo bot

> Como **operador**, quero **que o bot registre sinais periódicos de vida no MongoDB**
> para **detectar quando o processo travou mesmo sem erros visíveis nos logs**.

**Critérios de Aceitação:**

```text
DADO   que o bot está rodando normalmente
QUANDO 5 minutos passam após o início ou após o último heartbeat
ENTÃO  um documento é gravado na collection audit com event_type "heartbeat"
E      o documento contém process_uptime_seconds e timestamp
```

```text
DADO   que o bot travou (asyncio loop bloqueado)
QUANDO 10 minutos passam sem heartbeat
ENTÃO  GET /bot-activity retorna status "inactive"
E      GET /health da API retorna bot_process "dead"
```

- [ ] AC-01: Documento gravado na collection `audit` com estrutura definida na seção 5.1
- [ ] AC-02: Intervalo de 5 minutos entre heartbeats (tolerância de ±10 segundos)
- [ ] AC-03: Falha ao gravar heartbeat no MongoDB não interrompe o loop principal do bot
- [ ] AC-04: Heartbeat logado em structlog com level DEBUG (não INFO — evitar ruído)
- [ ] AC-05: Heartbeat não é gravado dentro de `TradingMonitor._tick()` — é uma task separada

---

### US-017-02: Healthcheck HTTP no container do bot

> Como **operador de infraestrutura**, quero **que o Docker saiba se o container do bot
> está saudável** para **ativar restart automático quando o processo travar**.

**Critérios de Aceitação:**

```text
DADO   que o processo bot está rodando
QUANDO o Docker daemon executa o healthcheck (curl http://localhost:8081/health)
ENTÃO  recebe resposta HTTP 200 com body {"status": "ok"}
```

```text
DADO   que o processo bot travou (container ainda em pé mas loop bloqueado)
QUANDO o Docker daemon executa o healthcheck e não recebe resposta em 5 segundos
ENTÃO  o healthcheck marca o container como unhealthy após N retries configurados
```

- [ ] AC-01: Servidor HTTP responde em `0.0.0.0:8081/health` com `200 {"status": "ok"}`
- [ ] AC-02: Timeout de resposta menor que 5 segundos em qualquer condição de carga
- [ ] AC-03: Porta 8081 não mapeada em `ports:` no docker-compose (apenas interna)
- [ ] AC-04: Servidor implementado em asyncio puro — sem dependência de biblioteca adicional
- [ ] AC-05: Falha do servidor HTTP não mata o processo bot (task isolada com try/except)

---

### US-017-03: Campo bot_process no /health da API atualizado

> Como **operador**, quero **que o GET /health da API do dashboard mostre se o bot está
> vivo** para **ter uma visão consolidada de saúde do sistema em um único endpoint**.

**Critérios de Aceitação:**

```text
DADO   que o bot gravou heartbeat há menos de 10 minutos
QUANDO GET /health é chamado na API do dashboard
ENTÃO  responde 200 com bot_process "alive"
```

```text
DADO   que nenhum heartbeat foi gravado nos últimos 10 minutos
QUANDO GET /health é chamado na API do dashboard
ENTÃO  responde 200 com bot_process "dead"
E      o campo last_heartbeat_at retorna o timestamp do último heartbeat (ou null)
```

- [ ] AC-01: `bot_process` retorna `"alive"` quando heartbeat recente (< 10 min)
- [ ] AC-02: `bot_process` retorna `"dead"` quando heartbeat ausente ou > 10 min
- [ ] AC-03: `bot_process` retorna `"unknown"` apenas quando MongoDB indisponível
      (mantém comportamento atual em caso de falha de infraestrutura)
- [ ] AC-04: Novo campo `last_heartbeat_at` (ISO 8601 ou null) adicionado à resposta
- [ ] AC-05: Falha ao consultar MongoDB para heartbeat não afeta os campos `status` e
      `mongodb` já existentes na resposta

---

## 5. Design e Arquitetura

### 5.1 Estrutura do Documento de Heartbeat (MongoDB)

```json
{
  "collection": "audit",
  "event_type": "heartbeat",
  "timestamp": "2026-05-06T15:00:00Z",
  "process_uptime_seconds": 3600,
  "monitor_count": 5,
  "metadata": {
    "source": "HeartbeatTask",
    "version": "1.0"
  }
}
```

Índice TTL na collection `audit` para este tipo de documento:

```json
{
  "index": {"timestamp": 1},
  "expireAfterSeconds": 86400,
  "partialFilterExpression": {"event_type": "heartbeat"}
}
```

**Nota:** O índice TTL é parcial — afeta apenas documentos `event_type: "heartbeat"`.
Outros documentos da collection `audit` (trades, sinais) não são afetados.

### 5.2 Contrato da HeartbeatTask

```python
# src/main.py — nova classe

class HeartbeatTask:
    """Grava sinal periódico de vida do processo na collection audit."""

    INTERVAL_SECONDS: int = 300  # 5 minutos

    def __init__(self, repo: MongoRepository, monitor_count: int) -> None:
        self._repo = repo
        self._monitor_count = monitor_count
        self._started_at = datetime.now(UTC)

    async def run(self) -> None:
        """Loop infinito: aguarda intervalo, grava heartbeat, repete."""
        while True:
            try:
                await asyncio.sleep(self.INTERVAL_SECONDS)
                await self._beat()
            except asyncio.CancelledError:
                return
            except Exception as exc:
                logger.debug(
                    "heartbeat_failed",
                    error_type=type(exc).__name__,
                )

    async def _beat(self) -> None:
        uptime = (datetime.now(UTC) - self._started_at).total_seconds()
        await self._repo.audit(
            "heartbeat",
            {
                "process_uptime_seconds": int(uptime),
                "monitor_count": self._monitor_count,
                "metadata": {"source": "HeartbeatTask", "version": "1.0"},
            },
        )
        logger.debug("heartbeat_recorded", uptime_seconds=int(uptime))
```

**Integração em `_main()`:**

```python
# Adicionar à lista de tasks em _main()
heartbeat_task = HeartbeatTask(repo=repo, monitor_count=len(monitors))
tasks.append(asyncio.create_task(heartbeat_task.run()))
```

### 5.3 Servidor HTTP Mínimo (asyncio puro)

```python
# src/main.py — função auxiliar

async def _health_server(host: str = "0.0.0.0", port: int = 8081) -> None:
    """Servidor HTTP mínimo para Docker healthcheck. Responde 200 em GET /health."""

    async def _handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            await reader.read(1024)  # consome a requisição
            response = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: application/json\r\n"
                b"Content-Length: 16\r\n"
                b"\r\n"
                b'{"status": "ok"}'
            )
            writer.write(response)
            await writer.drain()
        finally:
            writer.close()

    server = await asyncio.start_server(_handle, host, port)
    logger.info("health_server_started", host=host, port=port)
    async with server:
        await server.serve_forever()
```

**Integração em `_main()`:**

```python
tasks.append(asyncio.create_task(_health_server()))
```

### 5.4 Atualização do GET /health da API do Dashboard

```python
# src/api/routes/health.py — função auxiliar nova

_BOT_HEARTBEAT_THRESHOLD_MINUTES = 10

async def _get_bot_process_status(repo) -> tuple[str, str | None]:
    """Deriva bot_process e last_heartbeat_at do último heartbeat na collection audit.

    Retorna: (status, last_heartbeat_at_iso)
    status: "alive" | "dead" | "unknown"
    """
    try:
        last_heartbeat_at = await repo.get_last_heartbeat_at()
    except Exception:
        return "unknown", None

    if last_heartbeat_at is None:
        return "dead", None

    delta_minutes = (datetime.now(UTC) - last_heartbeat_at).total_seconds() / 60
    status = "alive" if delta_minutes <= _BOT_HEARTBEAT_THRESHOLD_MINUTES else "dead"
    return status, _to_iso8601(last_heartbeat_at)
```

**Novo método no MongoRepository:**

```python
# src/storage/repository.py

async def get_last_heartbeat_at(self) -> datetime | None:
    """Retorna o timestamp do último heartbeat gravado pelo processo bot.

    Consulta collection audit filtrando event_type == "heartbeat",
    ordenando por _id DESC, retorna generation_time do ObjectId.
    Retorna None se nenhum heartbeat encontrado.
    """
```

**Resposta atualizada do GET /health (200):**

```json
{
  "status": "ok",
  "mongodb": "ok",
  "bot_process": "alive",
  "last_heartbeat_at": "2026-05-06T15:00:00Z",
  "timestamp": "2026-05-06T15:02:00Z"
}
```

### 5.5 Atualização do docker-compose.yml

```yaml
# Serviço phicube — adicionar bloco healthcheck
phicube:
  # ... configuração existente mantida ...
  healthcheck:
    test: ["CMD-SHELL", "curl -f http://localhost:8081/health || exit 1"]
    interval: 30s
    timeout: 5s
    retries: 3
    start_period: 60s
```

**Nota:** `start_period: 60s` evita falso unhealthy durante o startup do bot (conexão
Binance + MongoDB pode levar alguns segundos). Se `curl` não estiver disponível no
container, alternativa: `["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8081/health')\""]`

### 5.6 Fluxo de Dados

```
src/main.py (processo bot)
  ├─ HeartbeatTask.run()         [a cada 5 min]
  │    └─ repo.audit("heartbeat", {...})  → collection audit (MongoDB)
  │
  └─ _health_server()            [sempre ativo, porta 8081]
       └─ GET /health → 200 {"status": "ok"}
            └─ docker healthcheck consome

src/api/main.py (processo dashboard-api)
  └─ GET /health
       ├─ repo.database.command("ping")          → mongodb: ok/error
       └─ repo.get_last_heartbeat_at()           → collection audit (MongoDB)
            └─ delta < 10 min → bot_process: "alive"
            └─ delta >= 10 min → bot_process: "dead"
            └─ MongoDB falha → bot_process: "unknown"
```

---

## 6. Regras de Negócio e Restrições

### 6.1 Invariantes de Negócio

| ID | Invariante | Violação → Ação |
|---|---|---|
| INV-017-01 | Falha do HeartbeatTask nunca para o processo bot | Exception capturada com log DEBUG; loop continua |
| INV-017-02 | Porta 8081 nunca exposta externamente | Sem entrada em `ports:` no docker-compose para o serviço `phicube` |
| INV-017-03 | bot_process retorna "unknown" apenas quando MongoDB indisponível | Distinguir ausência de heartbeat ("dead") de falha de infraestrutura ("unknown") |
| INV-017-04 | Índice TTL afeta apenas documentos event_type "heartbeat" | Usar `partialFilterExpression` — nunca apagar outros documentos de audit |
| INV-017-05 | Heartbeat não é gravado dentro de TradingMonitor._tick() | Task independente em _main(); nunca dentro do monitor de symbol/timeframe |

### 6.2 Validações Obrigatórias

- `HEARTBEAT_INTERVAL_SECONDS` fixo em 300 (não configurável via env nesta versão)
- `BOT_HEARTBEAT_THRESHOLD_MINUTES` fixo em 10 na API — constante, não query param
- `start_period` do healthcheck Docker deve ser >= 60s para evitar falso unhealthy no startup

### 6.3 Limitações Técnicas

- O servidor HTTP `_health_server()` responde `200 OK` para qualquer requisição recebida
  na porta 8081, independente do path — implementação mínima intencional
- `generation_time` do ObjectId tem precisão de 1 segundo — suficiente para threshold de 10 min
- Estado de saúde do bot via MongoDB tem latência de até 5 min + tempo de poll do dashboard
  (não é tempo-real — é suficiente para detecção operacional)

### 6.4 Padrões de Segurança

- Nunca logar conteúdo de exceções de rede — usar `type(exc).__name__` exclusivamente
- Porta 8081 não deve aparecer em `ports:` no docker-compose — healthcheck é interno

---

## 7. Testes e Validação

### 7.1 Testes Unitários

| ID | Descrição | Cenário | Prioridade |
|---|---|---|---|
| TEST_017_01 | HeartbeatTask._beat() grava na collection audit | Mock de repo.audit() → verifica chamada com event_type "heartbeat" | Alta |
| TEST_017_02 | HeartbeatTask falha ao gravar e não propaga exceção | repo.audit() lança Exception → loop continua sem crash | Alta |
| TEST_017_03 | GET /health retorna bot_process "alive" | last_heartbeat_at há 3 min → "alive" | Alta |
| TEST_017_04 | GET /health retorna bot_process "dead" | last_heartbeat_at há 15 min → "dead" | Alta |
| TEST_017_05 | GET /health retorna bot_process "dead" sem heartbeat | get_last_heartbeat_at() retorna None → "dead" | Alta |
| TEST_017_06 | GET /health retorna bot_process "unknown" com MongoDB down | get_last_heartbeat_at() lança Exception → "unknown" | Alta |
| TEST_017_07 | GET /health mantém campos existentes (status, mongodb, timestamp) | Todos os campos originais presentes na resposta enriquecida | Alta |
| TEST_017_08 | get_last_heartbeat_at() retorna datetime correto | Collection audit com heartbeat → retorna generation_time do _id mais recente | Alta |
| TEST_017_09 | get_last_heartbeat_at() retorna None sem heartbeats | Collection audit vazia ou sem event_type "heartbeat" → None | Alta |
| TEST_017_10 | _health_server responde 200 para GET /health | Servidor iniciado em porta aleatória → curl retorna 200 | Média |

### 7.2 Arquivos de Teste

```
tests/
├── test_heartbeat_task.py          (TEST_017_01, TEST_017_02)
├── api/
│   └── test_health_bot_process.py  (TEST_017_03 a TEST_017_07, TEST_017_10)
└── storage/
    └── test_repository_heartbeat.py (TEST_017_08, TEST_017_09)
```

### 7.3 Evidências Requeridas na PR

- [ ] `pytest tests/ --tb=short -q` com todos os 10+ testes passando
- [ ] `ruff check src/ tests/` sem erros
- [ ] Output de `docker inspect phicube-bot` mostrando `"Health": {"Status": "healthy"}`
      após deploy local
- [ ] Chamada `curl http://localhost:8080/health` mostrando `bot_process: "alive"` (não mais
      `"unknown"`) após 5 minutos de bot rodando
- [ ] Referência às seções desta SPEC impactadas no corpo da PR

---

## 8. Tratamento de Erros

| Erro / Condição | Causa | Ação do Sistema |
|---|---|---|
| MongoDB indisponível durante heartbeat | Container mongo down | Log DEBUG; HeartbeatTask continua no próximo ciclo |
| Porta 8081 já em uso no container | Conflito de porta | Log ERROR em startup; servidor HTTP não sobe; bot continua rodando |
| `curl` não disponível no container do bot | Imagem base sem curl | Usar alternativa Python no `healthcheck.test` do docker-compose |
| MongoDB indisponível durante GET /health (consulta heartbeat) | Container mongo down | bot_process retorna "unknown"; outros campos não afetados |
| HeartbeatTask cancelada no shutdown | SIGINT/SIGTERM | asyncio.CancelledError capturada; task encerra limpo |

---

## 9. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Índice TTL parcial na collection audit apagar documentos incorretos | Alto — perda de audit trail | Validar `partialFilterExpression` em teste de integração antes do merge |
| Servidor HTTP na porta 8081 conflitar com outro processo no container | Médio | Porta 8081 não é padrão; baixa probabilidade; verificar no Dockerfile |
| bot_process "alive" com bot travado num ciclo longo (timeout Binance) | Médio — falso positivo de saúde | Documentar como limitação conhecida: heartbeat é proxy de vida do processo, não de cada ciclo |
| start_period insuficiente no healthcheck Docker causando restart em startup normal | Médio — loop de restart | start_period conservador de 60s; ajustar se necessário após teste de deploy |

---

## 10. Definição de Pronto (DoD Global)

- [ ] SPEC aprovada pelo Time A
- [ ] OBJ-01: HeartbeatTask implementada, integrada em `_main()`, com testes passando
- [ ] OBJ-02: `_health_server()` implementado, integrado em `_main()`, com teste de integração
- [ ] OBJ-03: `docker-compose.yml` atualizado com healthcheck no serviço `phicube`
- [ ] OBJ-04: `GET /health` da API atualizado com `bot_process` e `last_heartbeat_at`
- [ ] OBJ-05: Índice TTL parcial criado em `MongoRepository.setup_indexes()`
- [ ] Invariantes INV-017-01 a INV-017-05 verificadas em testes
- [ ] `pytest tests/ --tb=short -q` com 100% das asserções críticas passando
- [ ] `ruff check src/ tests/` sem erros
- [ ] `docker inspect phicube-bot` retorna `"Status": "healthy"` em deploy local
- [ ] `GET /health` da API retorna `bot_process` diferente de `"unknown"` com bot ativo
- [ ] `docs/SDD/README.md` atualizado com SPEC_017 (status: Aprovada → Em Execução)

---

## 11. Plano de Entrega — Task Graph Sugerido

| Task | Descrição | Dependências |
|---|---|---|
| T1 | Verificar se `curl` está disponível no Dockerfile do bot; adicionar se ausente | — |
| T2 | Implementar `get_last_heartbeat_at()` no `MongoRepository` | — |
| T3 | Adicionar índice TTL parcial em `MongoRepository.setup_indexes()` | T2 |
| T4 | Implementar `HeartbeatTask` em `src/main.py` | T2 |
| T5 | Implementar `_health_server()` em `src/main.py` | — |
| T6 | Integrar `HeartbeatTask` e `_health_server()` nas tasks de `_main()` | T4, T5 |
| T7 | Atualizar `GET /health` em `src/api/routes/health.py` (bot_process + last_heartbeat_at) | T2 |
| T8 | Atualizar `docker-compose.yml` com healthcheck no serviço `phicube` | T1, T5 |
| T9 | Implementar testes unitários (10 testes em 3 arquivos) | T2, T4, T7 |
| T10 | Teste de integração: deploy local + `docker inspect` + curl no /health da API | T6, T8, T9 |

---

## Histórico

- **2026-05-06:** Criação da SPEC_017 pelo Time A. Caminho C (Heartbeat MongoDB +
  Healthcheck HTTP) aprovado pelo operador. Status: Em Refinamento.
