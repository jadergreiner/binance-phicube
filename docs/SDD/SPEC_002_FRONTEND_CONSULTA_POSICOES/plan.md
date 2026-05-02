# Plan — SPEC_002: Frontend de Consulta de Posições

**spec_id:** SPEC_002
**status:** Revisado — pronto para tasks
**data:** 2026-05-02
**autor:** Time A (Refinamento)

---

## Rastreabilidade

```text
MANIFESTO.md
  └─ Princípio 3 (Transparência total) → registrar e auditar decisões do operador
  └─ Princípio 5 (Segurança das credenciais) → nunca expor chaves em código ou logs
  └─ Princípio 6 (Operação contínua e resiliente) → tolerar falhas, reconectar
  └─ "uso pessoal, instância única" → porta local, sem multi-usuário
        ↓
PRD.md — Fase 2 (Expansão) → "Dashboard de performance em tempo real"
  └─ Restrição de Segurança → container roda com user não-root
  └─ Restrição de Segurança → chaves apenas em variáveis de ambiente via .env
  └─ Out of Scope v1 → "Dashboard web full-featured" (≠ esta SPEC — escopo mínimo)
        ↓
SPEC_001 → Motor de dados (PositionStream, AdaptiveUpdater, DashboardSnapshotBuilder)
        ↓
SPEC_002 → Frontend mínimo de consulta (esta SPEC)
```

---

## Meta

- **spec_id:** SPEC_002
- **prd_fase:** Fase 2 — Expansão (`PRD.md › Sprint 7+ › Dashboard`)
- **objetivo:** Expor interface web local (FastAPI + HTML/JS vanilla) para consulta em tempo real das posições abertas, reutilizando integralmente a infraestrutura de dados da SPEC_001 sem duplicar lógica de negócio.
- **escopo:** API FastAPI (REST + WebSocket), frontend HTML/JS vanilla sem build step, container `dashboard-api` no docker-compose, porta vinculada a `127.0.0.1`.
- **fora_de_escopo:** Autenticação, HTTPS, React/Vue, ações de trade, histórico, alertas externos, segundo `DashboardClient`, "Dashboard web full-featured" (Out of Scope PRD v1).
- **principios_manifesto_aplicados:** Princípios 3 (Transparência), 5 (Segurança), 6 (Resiliência).

---

## Decisões Arquiteturais (Time A — sessão 2026-05-01)

| Decisão | Escolha | Justificativa |
|---|---|---|
| Framework backend | FastAPI + uvicorn | Async nativo, WebSocket suportado, `StaticFiles` integrado, alinha com stack Python do projeto. |
| Framework frontend | HTML + JS vanilla (sem build step) | Entrega rápida, zero dependência de node/npm no Docker, migrável para React futuramente sem mudar a API. |
| Transporte principal | WebSocket `/ws/positions` (push do backend) | `PositionStream` já mantém estado em memória; push elimina polling desnecessário no frontend. |
| Transporte secundário | `GET /positions` (REST, fallback/debug) | Permite `curl`, health check e snapshot inicial antes de WS conectar. |
| Processo | Isolado — container `dashboard-api` próprio | Evita acoplamento de ciclo de vida entre bot de trading e API. Cada container tem seu `PositionStream` READ_ONLY. |
| MongoDB no container API | Sim — acesso ao mesmo MongoDB | Permite exibir dados em modo `cached` pós-restart sem conexão Binance, usando `DashboardCache` da SPEC_001. |
| Porta HTTP | `127.0.0.1:8080` — nunca `0.0.0.0` | Critério de segurança não negociável do Time A. Uso solo, rede local. |
| Lógica de negócio no JS | Proibida | JS renderiza payload recebido do backend. `DashboardSnapshotBuilder` reside no Python. |
| Dependências externas no frontend | Proibidas (sem CDN) | Ambiente Docker pode não ter internet; zero risco de supply chain via CDN. |

---

## Entradas

- `MANIFESTO.md` — princípios inegociáveis do projeto (Segurança, Transparência, Resiliência)
- `PRD.md` — Fase 2 (Dashboard), Restrições de Segurança (user não-root, chaves em env)
- `docs/SDD/SPEC_002_FRONTEND_CONSULTA_POSICOES/SPEC.md`
- `docs/SDD/SPEC_001_PAINEL_POSICOES_TEMPO_REAL/SPEC.md` (infraestrutura de dados consumida)
- `src/dashboard/__init__.py` (contratos públicos: `AdaptiveUpdater`, `DashboardClient`, `DashboardClientError`)
- `contracts/task.json` (template de contrato de task)
- `docker-compose.yml` (serviço base a ser estendido)

---

## Premissas

- SPEC_001 está 100% implementada e testada — `PositionStream`, `AdaptiveUpdater`, `DashboardClient`, `DashboardSnapshotBuilder` disponíveis.
- Credenciais `DASHBOARD_API_KEY` e `DASHBOARD_API_SECRET` já existem no `.env` — nunca em código ou logs (**MANIFESTO Princípio 5**).
- MongoDB acessível pelo container `dashboard-api` via rede interna do Docker Compose.
- FastAPI e uvicorn serão adicionados ao `pyproject.toml` como dependências do projeto (PRD não lista FastAPI explicitamente — atualização necessária no PRD após esta SPEC).
- O operador acessa o frontend via `http://127.0.0.1:8080` no browser local — uso pessoal, instância única (**MANIFESTO**).
- Container `dashboard-api` roda com **user não-root** (**PRD › Restrições de Segurança**).

---

## Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Dois listenKeys simultâneos (bot + API) para a mesma conta | Médio | Aceito — `DashboardClient` usa Key READ_ONLY dedicada; bot usa Key de trade separada. Binance suporta múltiplos listenKeys por conta. |
| Porta `0.0.0.0` exposta acidentalmente no compose | Alto | `@security-audit` valida `docker-compose.yml` antes do merge; critério de aceite explícito na task de Docker. **`mongo-express` tem esse problema hoje — não replicar.** |
| Duas implementações de serialização divergem | Alto | Função `serialize_snapshot` centralizada — única fonte de verdade para REST e WebSocket. |
| `PositionStream` sem mecanismo de notificação para a API | Alto | Adicionar `on_update` callback list na Fase 1 do `PositionStream` antes de implementar o WebSocket. |
| JS reimplementar lógica de status/alerta | Médio | INV-002-03 proíbe; `@qa-review` revisa o `app.js` na PR. |
| Frontend em tela em branco sem posições abertas | Baixo | Critério de aceite explícito: estado vazio deve exibir mensagem, não tela branca. |
| Versão incompatível de FastAPI/uvicorn com Python 3.11 | Baixo | Versões fixadas no `pyproject.toml`; testado antes do primeiro commit. |
| WebSocket do frontend não reconecta após queda | Médio | Reconexão automática com backoff é critério de aceite da US-002-02. |

---

## Estratégia de Execução

As fases são **sequenciais** — cada fase é pré-requisito da seguinte.

### Fase 1 — Infraestrutura da API (pré-requisito bloqueante)

- Adicionar FastAPI e uvicorn ao `pyproject.toml`.
- Criar `src/api/__init__.py` e `src/api/main.py` com app FastAPI + lifespan.
- Lifespan: instanciar `DashboardClient` → `PositionStream.start()` → `AdaptiveUpdater.start(stream)` no startup; inverso no shutdown.
- Expor instância de `PositionStream` via `app.state.stream`.
- Criar `Dockerfile.api` (ou target no Dockerfile existente) para o container da API.

### Fase 2 — Endpoints REST

- Criar `src/api/routes/positions.py`.
- Implementar `GET /health` — retorna `ConnectionStatus` do stream.
- Implementar `GET /positions` — retorna snapshot serializado: `{"positions": [...], "summary": {...}, "status": "..."}`.
- Implementar função `serialize_snapshot(stream) -> dict` centralizando a serialização de `PositionView` e `AccountSummary` para JSON (dataclasses → dict, datetime → ISO 8601). **Esta função é a única implementação de serialização — reutilizada também no handler WebSocket da Fase 3.**
- Retornar 503 quando stream não estiver ativo.

### Fase 3 — WebSocket `/ws/positions`

- Implementar endpoint WebSocket em `src/api/routes/positions.py`.
- Ao conectar: enviar snapshot imediato usando **a mesma função de serialização** da Fase 2 (não duplicar).
- Adicionar callback `on_update` ao `PositionStream` — lista de callbacks async, padrão consistente com `on_status_change` já existente — para notificar handlers ativos a cada mudança de posição.
- A cada atualização: serializar e enviar payload completo (não diff) para todos os clientes conectados.
- Tratar desconexão do cliente sem propagar exceção para o stream.
- Gerenciar lista de clientes WebSocket ativos no `app.state`.
- URL do WebSocket no frontend usa caminho **relativo** (`/ws/positions`) — funciona independente da ordem de entrega das fases.

### Fase 4 — Frontend HTML/JS Vanilla

- Criar `src/frontend/static/index.html` — estrutura da página: tabela de posições, card de resumo, indicador de status, banner de alerta.
- Criar `src/frontend/static/app.js` — lógica de conexão WebSocket, renderização da tabela, renderização do card, exibição de banner por status, reconexão automática com backoff.
- Criar `src/frontend/static/style.css` — estilo mínimo operacional.
- Montar `StaticFiles` no FastAPI apontando para `src/frontend/static/`.
- `GET /` deve redirecionar ou servir `index.html`.
- Validar: sem `<script src="https://...">`, sem CDN, sem dependências externas.

### Fase 5 — Docker Compose

- Adicionar serviço `dashboard-api` ao `docker-compose.yml`.
- Porta vinculada a `127.0.0.1:8080:8080` — critério de segurança obrigatório. **Não replicar o padrão incorreto do `mongo-express` (porta sem `127.0.0.1`).**
- Credenciais via `env_file: .env` — padrão do projeto, não declarar variáveis individualmente (**MANIFESTO Princípio 5**).
- Container roda com **user não-root** no Dockerfile — obrigatório (**PRD › Restrições de Segurança**).
- `depends_on: mongo` (nome real do serviço no compose — não `mongodb`).
- `restart: unless-stopped`.
- Incluir na rede `phicube-net` para acesso ao MongoDB.

### Fase 6 — Testes e Validação

- Testes unitários TEST_002_01 a TEST_002_05 (endpoints REST + WebSocket + lifespan).
- Testes de integração INT_002_01 a INT_002_03 (container real, posições reais, reconexão).
- Evidências obrigatórias conforme SPEC_002 seção 7.3.
- `@security-audit`: porta, secrets, CORS, CDN ausente.
- `@qa-review`: cobertura, estado vazio, reconexão WS.

---

## Dependências

- SPEC_001 100% implementada (bloqueante).
- FastAPI e uvicorn disponíveis no ambiente (adicionar ao `pyproject.toml`).
- MongoDB acessível na rede Docker (já disponível).
- Credenciais `DASHBOARD_API_KEY` / `DASHBOARD_API_SECRET` no `.env` (já configuradas na SPEC_001).
- Browser local para validação manual do frontend.

---

## Notas de Consistência

- **PRD desatualizado:** `PRD.md › Requisitos Técnicos › Stack` não lista FastAPI. Time B deve registrar atualização do PRD como item pós-merge desta SPEC.
- **`mongo-express` no compose** tem porta exposta sem `127.0.0.1` — inconsistência de segurança preexistente, fora do escopo desta SPEC, mas registrada para tratamento futuro.

---

## Critérios de Pronto do Plano

- [x] Plano rastreável para a SPEC_002.
- [x] Rastreabilidade MANIFESTO → PRD → SPEC_001 → SPEC_002 explicitada.
- [x] Decisões arquiteturais registradas com justificativa.
- [x] Dependências mapeadas (incluindo SPEC_001 como bloqueante).
- [x] Riscos com mitigação definida.
- [x] Princípios do MANIFESTO e restrições do PRD referenciados nas fases.
- [x] Fases sequenciais com pré-requisitos claros.
- [x] Pronto para gerar `tasks.json`.
