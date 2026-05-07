# SPEC_016 — Visibilidade Operacional Completa no Dashboard

**ID:** SPEC_016
**Status:** Concluída
**Data:** 2026-05-06
**Autor:** Time A (Refinamento)
**Executores:** Time B (Execução)
**Skills requeridas:** Python, FastAPI, asyncio, motor, structlog, pytest, HTML/CSS/JS
**Depende de:** SPEC_001, SPEC_002, SPEC_003, SPEC_006, SPEC_010, SPEC_012
**Skill de validação:** `sdd-spec-driven-development`, `qa-review`

---

## 1. Título e Resumo

### 1.1 Nome da Funcionalidade

Visibilidade Operacional Completa no Dashboard

### 1.2 Resumo (High-Level Definition)

**O que é:** Quatro melhorias na camada de visualização e API do dashboard existente:
(1) exibição de SL e TP na tabela de posições abertas; (2) painel de histórico dos últimos
50 trades fechados; (3) indicador de saúde do bot com detecção de inatividade; (4) filtros
interativos de símbolo e direção na tabela de posições.

**Por que estamos fazendo:** O operador atualmente não consegue ver, no painel, os níveis de
proteção das posições abertas, o histórico recente de resultados, nem saber se o bot está
operacional — informações que são críticas para acompanhamento intraday sem acesso ao terminal.

**Valor de negócio:** Elimina a necessidade de o operador chamar endpoints da API manualmente
para informações operacionais básicas; aumenta a confiança de que o bot está ativo e as posições
estão protegidas; acelera a identificação de trades em lucro ou prejuízo.

**Conexão com PRD/SPEC:** PRD §MVP item 4 — "Proteção de todas as posições abertas";
PRD §Fase 2 — "Dashboard de performance em tempo real". Complementa SPEC_010 (performance)
e SPEC_012 (monitoramento ativo).

---

## 2. Objetivos e Escopo

### 2.1 Objetivos (o que será entregue)

- [x] **OBJ-01:** Colunas SL e TP visíveis na tabela de posições abertas (frontend + endpoint)
- [x] **OBJ-02:** Painel de histórico com os últimos 50 trades fechados (novo endpoint + frontend)
- [x] **OBJ-03:** Indicador de saúde do bot com threshold de 10 minutos (novo endpoint + frontend)
- [x] **OBJ-04:** Filtros interativos de símbolo e direção na tabela de posições (frontend only)

### 2.2 Fora do Escopo (Non-Goals)

- **Não inclui:** Paginação do histórico de trades — 50 registros fixos é o escopo desta SPEC
- **Não inclui:** Filtros de data ou período no histórico — deferred
- **Não inclui:** Recolocação automática de SL/TP pelo dashboard — dashboard é somente leitura
  (invariante do projeto desde SPEC_001)
- **Não inclui:** Alertas push ou notificações de inatividade via Telegram — apenas indicador
  visual no painel; Telegram já é coberto pela SPEC_012 para eventos críticos
- **Não inclui:** Edição ou cancelamento de ordens pelo frontend
- **Não inclui:** Histórico de sinais não executados

---

## 3. Referências

| Documento | Seção | Relevância |
|---|---|---|
| `SPEC_001/SPEC.md` | §Invariantes | Dashboard é somente leitura — nunca executa ordens |
| `SPEC_006/SPEC.md` | — | Métricas de trades fechados (pré-requisito) |
| `SPEC_010/SPEC.md` | §5.2 | Padrão de endpoints de performance consumidos no frontend |
| `SPEC_012/SPEC.md` | §5.4 | Campos `stop_loss` e `take_profit` na collection `trades` |
| `src/trading/order_manager.py` | `Trade.to_dict()` | Campos canônicos: `stop_loss`, `take_profit` |
| `src/api/routes/health.py` | — | Rota base `/health` a ser complementada |
| `src/api/routes/positions.py` | — | Rota de posições existente |
| `src/storage/repository.py` | `get_performance_metrics()` | Padrão de consulta MongoDB |

---

## 4. Histórias de Usuário e Requisitos

### US-016-01: SL e TP visíveis na tabela de posições abertas

> Como **operador**, quero **ver o nível de Stop Loss e Take Profit de cada posição aberta
> no painel** para **confirmar que todas as posições estão protegidas sem abrir o terminal**.

**Critérios de Aceitação:**

```text
DADO   que existem posições abertas com trades OPEN no MongoDB
QUANDO o painel carrega ou atualiza via polling
ENTÃO  a tabela de posições exibe colunas "SL" e "TP" com os valores de stop_loss
       e take_profit do trade correspondente
```

- [ ] AC-01: Coluna "SL" exibe o valor de `stop_loss` do documento `trades` com status `OPEN`
      correspondente ao símbolo da posição
- [ ] AC-02: Coluna "TP" exibe o valor de `take_profit` do documento `trades` com status `OPEN`
      correspondente ao símbolo da posição
- [ ] AC-03: Quando não existe trade OPEN no MongoDB para o símbolo (posição aberta diretamente
      na exchange, fora do bot), as colunas exibem "—"
- [ ] AC-04: Valores formatados com 4 casas decimais, alinhados com as demais colunas de preço
- [ ] AC-05: Posição sem SL (campo `stop_loss` ausente ou nulo) exibe "—" em vermelho (alerta visual)

---

### US-016-02: Histórico dos últimos 50 trades fechados

> Como **operador**, quero **ver os últimos 50 trades fechados no painel** para **acompanhar
> resultados recentes sem precisar acessar a API ou o MongoDB diretamente**.

**Critérios de Aceitação:**

```text
DADO   que existem trades com status CLOSED_TP, CLOSED_SL ou CLOSED_MANUAL no MongoDB
QUANDO o operador visualiza o painel
ENTÃO  uma tabela exibe os últimos 50 trades fechados, ordenados do mais recente para o mais antigo
```

- [ ] AC-01: Endpoint `GET /trades/history` retorna array com os últimos 50 trades fechados,
      ordenados por `closed_at` decrescente
- [ ] AC-02: Cada registro contém: `symbol`, `timeframe`, `direction`, `entry_price`, `exit_price`,
      `stop_loss`, `take_profit`, `pnl_usdt`, `status`, `opened_at`, `closed_at`
- [ ] AC-03: Trades com status `FAILED` são excluídos do histórico
- [ ] AC-04: PnL positivo exibido em verde; negativo em vermelho na tabela do frontend
- [ ] AC-05: `pnl_usdt` nulo (trade sem PnL registrado) exibe "—"
- [ ] AC-06: Sem trades fechados → tabela exibe mensagem "Nenhum trade fechado encontrado."
- [ ] AC-07: Polling automático a cada 60 segundos (mesmo padrão da seção de performance)

---

### US-016-03: Indicador de saúde do bot

> Como **operador**, quero **ver no painel se o bot está ativo** para **identificar imediatamente
> se o sistema parou de operar sem precisar verificar logs ou containers**.

**Critérios de Aceitação:**

```text
DADO   que o bot está operando normalmente (ciclos de 5 minutos)
QUANDO o painel carrega ou atualiza
ENTÃO  um indicador visual exibe "BOT ATIVO" com o timestamp do último ciclo detectado
```

```text
DADO   que o último documento registrado em `signals` ou `audit` é anterior a 10 minutos
QUANDO o painel atualiza
ENTÃO  o indicador muda para "BOT INATIVO" com o timestamp da última atividade detectada
```

- [ ] AC-01: Endpoint `GET /bot-activity` retorna `last_activity_at` (ISO 8601), `status`
      (`"active"` ou `"inactive"`), `minutes_since_last_activity` e `threshold_minutes` (10)
- [ ] AC-02: `status = "inactive"` quando `(now_utc - last_activity_at) > 10 minutos`
- [ ] AC-03: `last_activity_at` é derivado do documento mais recente nas collections `signals`
      ou `audit` (busca `$sort: {_id: -1}, $limit: 1` em ambas, retorna o mais recente entre as duas)
- [ ] AC-04: Quando MongoDB não tem nenhum documento em `signals` nem `audit`, retorna
      `status = "inactive"`, `last_activity_at = null`
- [ ] AC-05: Indicador visual: badge verde com texto "ATIVO" quando active; badge vermelho com
      texto "INATIVO" quando inactive
- [ ] AC-06: Tooltip ou subtexto exibe "Último ciclo: HH:MM:SS" formatado em horário local do browser
- [ ] AC-07: Polling automático a cada 30 segundos (intervalo menor que os demais por ser
      indicador de saúde crítico)
- [ ] AC-08: Falha no endpoint `/bot-activity` não afeta o painel de posições (try/catch isolado)

---

### US-016-04: Filtros interativos na tabela de posições

> Como **operador**, quero **filtrar a tabela de posições abertas por símbolo e por direção**
> para **focar rapidamente nas posições relevantes quando há muitos ativos abertos**.

**Critérios de Aceitação:**

```text
DADO   que existem posições abertas de múltiplos símbolos e direções (LONG e SHORT)
QUANDO o operador seleciona um símbolo no filtro ou uma direção (LONG/SHORT/Todos)
ENTÃO  a tabela exibe apenas as posições que correspondem ao filtro aplicado
```

- [ ] AC-01: Dropdown de símbolo populado dinamicamente com os símbolos das posições atuais,
      mais opção "Todos"
- [ ] AC-02: Botões de direção: "Todos" | "LONG" | "SHORT" (toggle exclusivo)
- [ ] AC-03: Filtros são aplicados localmente no frontend (sem nova chamada à API)
- [ ] AC-04: Filtros combinam: símbolo AND direção
- [ ] AC-05: Sem posições após filtro → tabela exibe "Nenhuma posição encontrada para os
      filtros selecionados."
- [ ] AC-06: Filtros são resetados quando a tabela atualiza via WebSocket (comportamento
      esperado: atualização sobrescreve o DOM; filtros reativados após render)
- [ ] AC-07: Implementação exclusivamente em JavaScript no `app.js` existente — sem
      mudanças em backend

---

## 5. Design e Arquitetura

### 5.1 Novos Endpoints de Backend

#### `GET /trades/history`

```python
# src/api/routes/trades.py  (novo arquivo)
@router.get("/trades/history")
async def get_trade_history(request: Request) -> JSONResponse:
    """Retorna os últimos 50 trades fechados, ordenados por closed_at DESC.

    Exclui status OPEN e FAILED.
    Retorna 503 se MongoDB indisponível.
    """
```

**Query MongoDB:**

```python
pipeline = [
    {"$match": {"status": {"$in": ["CLOSED_TP", "CLOSED_SL", "CLOSED_MANUAL"]}}},
    {"$sort": {"closed_at": -1}},
    {"$limit": 50},
    {"$project": {
        "_id": 0,
        "symbol": 1,
        "timeframe": 1,
        "direction": 1,
        "entry_price": 1,
        "exit_price": 1,
        "stop_loss": 1,
        "take_profit": 1,
        "pnl_usdt": 1,
        "status": 1,
        "opened_at": 1,
        "closed_at": 1,
    }}
]
```

**Resposta de sucesso (200):**

```json
{
  "trades": [
    {
      "symbol": "BTCUSDT",
      "timeframe": "1h",
      "direction": "long",
      "entry_price": 65000.0,
      "exit_price": 67000.0,
      "stop_loss": 63500.0,
      "take_profit": 68000.0,
      "pnl_usdt": 42.50,
      "status": "CLOSED_TP",
      "opened_at": "2026-05-06T10:00:00Z",
      "closed_at": "2026-05-06T14:30:00Z"
    }
  ],
  "total": 1,
  "generated_at": "2026-05-06T15:00:00Z"
}
```

**Resposta de erro (503):**

```json
{"detail": "Repositório indisponível"}
```

---

#### `GET /bot-activity`

```python
# src/api/routes/health.py  (extensão da rota existente)
@router.get("/bot-activity")
async def get_bot_activity(request: Request) -> JSONResponse:
    """Verifica atividade recente do bot consultando as collections signals e audit.

    Retorna status 'active' se último documento foi inserido há menos de 10 minutos.
    Retorna status 'inactive' caso contrário ou se não há documentos.
    Nunca retorna 503 — degradação silenciosa com status inactive.
    """
```

**Lógica de detecção:**

```python
_INACTIVITY_THRESHOLD_MINUTES = 10

# ObjectId embute timestamp de criação — não exige campo explícito `timestamp`
last_signal = await db["signals"].find_one({}, sort=[("_id", -1)])
last_audit  = await db["audit"].find_one({}, sort=[("_id", -1)])

candidates = [doc for doc in [last_signal, last_audit] if doc is not None]
if not candidates:
    last_activity_at = None
else:
    last_activity_at = max(doc["_id"].generation_time for doc in candidates)

now_utc = datetime.now(UTC)
if last_activity_at is None:
    status = "inactive"
    minutes_since = None
else:
    delta = (now_utc - last_activity_at).total_seconds() / 60
    status = "active" if delta <= _INACTIVITY_THRESHOLD_MINUTES else "inactive"
    minutes_since = round(delta, 1)
```

**Resposta (200 — sempre):**

```json
{
  "status": "active",
  "last_activity_at": "2026-05-06T14:58:00Z",
  "minutes_since_last_activity": 2.3,
  "threshold_minutes": 10,
  "checked_at": "2026-05-06T15:00:00Z"
}
```

Quando sem atividade:

```json
{
  "status": "inactive",
  "last_activity_at": null,
  "minutes_since_last_activity": null,
  "threshold_minutes": 10,
  "checked_at": "2026-05-06T15:00:00Z"
}
```

---

#### `GET /positions` — Extensão para incluir SL/TP

O endpoint existente em `src/api/routes/positions.py` retorna dados da exchange via
`DashboardClient`. Para cruzar com SL/TP do MongoDB, o Time B deve:

1. Buscar trades com `status = "OPEN"` no MongoDB: `{"status": "OPEN"}`, projetando
   `{symbol, stop_loss, take_profit}`
2. Construir dict `{symbol: {sl_price, tp_price}}` em memória
3. Para cada posição retornada pela exchange, enriquecer com os campos `sl_price` e
   `tp_price` do dict (ou `null` se símbolo não encontrado)
4. Os campos adicionados na resposta JSON usam os nomes `"sl_price"` e `"tp_price"`
   para clareza no frontend (mapeados de `stop_loss` e `take_profit` na collection)

**Resposta enriquecida — posição com trade OPEN:**

```json
{
  "symbol": "BTCUSDT",
  "side": "long",
  "sl_price": 63500.0,
  "tp_price": 68000.0,
  "...": "...campos existentes..."
}
```

**Resposta enriquecida — posição sem trade OPEN correspondente:**

```json
{
  "symbol": "ETHUSDT",
  "side": "long",
  "sl_price": null,
  "tp_price": null,
  "...": "...campos existentes..."
}
```

---

### 5.2 Novos Métodos no MongoRepository

```python
# src/storage/repository.py

async def get_trade_history(self, limit: int = 50) -> list[dict]:
    """Retorna os últimos N trades fechados, ordenados por closed_at DESC.

    Exclui OPEN e FAILED. Campos: symbol, timeframe, direction,
    entry_price, exit_price, stop_loss, take_profit, pnl_usdt,
    status, opened_at, closed_at.
    """

async def get_open_trade_sl_tp(self) -> dict[str, dict]:
    """Retorna dict {symbol: {sl_price, tp_price}} para todos os trades OPEN.

    Utilizado pelo endpoint /positions para enriquecer dados da exchange.
    Retorna {} se não há trades OPEN.
    """
```

---

### 5.3 Novo Arquivo de Rota

```text
src/
└── api/
    └── routes/
        ├── health.py       (existente — adicionar /bot-activity aqui)
        └── trades.py       (novo — endpoint /trades/history)
```

O novo router de `trades.py` deve ser registrado em `src/api/main.py` com prefixo vazio,
mantendo consistência com as demais rotas existentes.

---

### 5.4 Mudanças no Frontend

**Estrutura HTML adicionada em `index.html`:**

```html
<!-- Indicador de saúde do bot — adicionado na seção hero -->
<div id="bot-status-indicator" class="bot-status-badge">
  <span id="bot-status-dot"></span>
  <span id="bot-status-text">—</span>
  <span id="bot-status-time"></span>
</div>

<!-- Filtros de posições — adicionados antes da tabela de posições -->
<section class="positions-filters">
  <select id="filter-symbol">
    <option value="">Todos os símbolos</option>
  </select>
  <div class="direction-toggle">
    <button class="dir-btn active" data-dir="">Todos</button>
    <button class="dir-btn" data-dir="long">LONG</button>
    <button class="dir-btn" data-dir="short">SHORT</button>
  </div>
</section>

<!-- Histórico de trades — nova seção após performance -->
<section class="trade-history-panel">
  <h2>Histórico de Trades</h2>
  <div class="table-wrap">
    <table class="trade-history-table">
      <thead>
        <tr>
          <th>Símbolo</th><th>TF</th><th>Direção</th>
          <th>Entrada</th><th>Saída</th><th>SL</th><th>TP</th>
          <th>PnL (USDT)</th><th>Status</th><th>Fechado em</th>
        </tr>
      </thead>
      <tbody id="trade-history-body">
        <tr class="empty-row"><td colspan="10">Sem dados.</td></tr>
      </tbody>
    </table>
  </div>
</section>
```

**Colunas SL/TP adicionadas na tabela de posições existente:**

As colunas "SL" e "TP" são inseridas após "Entry" e antes de "Mark" na tabela de posições abertas.
Posição com `sl_price: null` recebe classe CSS `sl-missing` na célula (exibição vermelha).

**Funções JavaScript adicionadas em `app.js`:**

```javascript
// Polling bot activity — 30s
async function fetchBotActivity() { ... }
function renderBotStatus(data) { ... }

// Polling histórico — 60s
async function fetchTradeHistory() { ... }
function renderTradeHistory(trades) { ... }

// Filtros de posições — client-side
function applyPositionFilters() { ... }
function populateSymbolFilter(positions) { ... }

// Adicionar ao bootstrap():
setInterval(fetchBotActivity, 30_000);
setInterval(fetchTradeHistory, 60_000);
fetchBotActivity();
fetchTradeHistory();
```

---

### 5.5 Fluxo de Dados — SL/TP nas Posições

```text
Frontend (polling 5s via /positions)
  └─ GET /positions
       ├─ DashboardClient.get_positions()         [dados da exchange]
       └─ repository.get_open_trade_sl_tp()       [dados do MongoDB]
            └─ enriquecimento: {sl_price, tp_price} por símbolo
                 └─ JSON enriquecido → frontend → tabela com SL/TP
```

---

### 5.6 Fluxo de Dados — Indicador de Saúde

```text
Frontend (polling 30s via /bot-activity)
  └─ GET /bot-activity
       ├─ db["signals"].find_one({}, sort=[("_id", -1)])
       └─ db["audit"].find_one({}, sort=[("_id", -1)])
            └─ max(generation_time) → delta → status
                 └─ JSON → frontend → badge ATIVO/INATIVO
```

---

## 6. Regras de Negócio e Invariantes

### 6.1 Invariantes de Negócio

| ID | Invariante | Violação → Ação |
|---|---|---|
| INV-016-01 | Dashboard é somente leitura — nenhuma ação de escrita exposta | Nenhum endpoint POST/PUT/DELETE permitido nesta SPEC |
| INV-016-02 | Falha em qualquer novo endpoint não afeta o painel de posições existente | try/catch isolado por funcionalidade em `app.js` |
| INV-016-03 | `GET /bot-activity` nunca retorna 503 — sempre 200 com status degradado | Exceção MongoDB → `status: "inactive"`, `last_activity_at: null` |
| INV-016-04 | Histórico exclui trades FAILED | Query sempre filtra `status NOT IN [OPEN, FAILED]` |
| INV-016-05 | Posição sem SL no MongoDB exibe alerta visual vermelho | `sl_price: null` → célula com classe CSS `sl-missing` |
| INV-016-06 | Filtros de posição são client-side — não geram chamadas adicionais à API | `applyPositionFilters()` opera sobre dados já em memória |
| INV-016-07 | Logs de novos endpoints nunca expõem credenciais ou tokens | `type(exc).__name__` exclusivamente em blocos except |

### 6.2 Validações Obrigatórias

- `limit` fixo em 50 no `get_trade_history()` — não exposto como parâmetro de query
- `threshold_minutes` fixo em 10 — constante `_INACTIVITY_THRESHOLD_MINUTES = 10`, não configurável via query param
- `stop_loss` e `take_profit` lidos da collection `trades` — campo canônico é `stop_loss`
  (ver `Trade.to_dict()` em `src/trading/order_manager.py`; não existe campo `sl_price` na collection)
- `_id.generation_time` em ObjectId retorna `datetime` timezone-aware em UTC — compatível com
  `datetime.now(UTC)` sem conversão adicional

### 6.3 Limitações Técnicas

- O cruzamento posição-trade por `symbol` assume máximo de uma posição aberta por símbolo
  (invariante existente desde SPEC_001)
- `generation_time` do ObjectId tem precisão de 1 segundo — suficiente para threshold de 10 min
- Polling de 30s no indicador de saúde gera no máximo 2 req/min — carga desprezível
- Filtros são resetados ao receber novo snapshot WebSocket — documentado como comportamento
  esperado (AC-06 da US-016-04)

---

## 7. Testes e Validação

### 7.1 Testes Unitários

| ID | Descrição | Cenário | Prioridade |
|---|---|---|---|
| TEST_016_01 | `GET /trades/history` retorna 200 com até 50 trades | MongoDB com 60 trades fechados → retorna 50 | Alta |
| TEST_016_02 | `GET /trades/history` exclui OPEN e FAILED | Trades mistos → apenas CLOSED_* retornados | Alta |
| TEST_016_03 | `GET /trades/history` retorna 200 com array vazio | Sem trades fechados → `{"trades": [], "total": 0}` | Alta |
| TEST_016_04 | `GET /trades/history` retorna 503 sem MongoDB | `app.state.repository = None` → 503 | Alta |
| TEST_016_05 | `GET /bot-activity` retorna "active" | Último doc em signals < 10 min → `"status": "active"` | Alta |
| TEST_016_06 | `GET /bot-activity` retorna "inactive" por tempo | Último doc em signals > 10 min → `"status": "inactive"` | Alta |
| TEST_016_07 | `GET /bot-activity` retorna inactive sem documentos | Collections vazias → `last_activity_at: null` | Alta |
| TEST_016_08 | `GET /bot-activity` usa o mais recente entre signals e audit | audit mais recente → usa audit | Alta |
| TEST_016_09 | `GET /bot-activity` retorna 200 mesmo com falha no MongoDB | Exception → 200 com status inactive | Alta |
| TEST_016_10 | `GET /positions` enriquece com sl_price e tp_price | Trade OPEN no MongoDB → campos presentes | Alta |
| TEST_016_11 | `GET /positions` retorna null para sl/tp sem trade OPEN | Sem trade OPEN → null | Alta |
| TEST_016_12 | `get_trade_history()` ordena por closed_at DESC | Trades fora de ordem → retorno ordenado | Média |
| TEST_016_13 | `get_open_trade_sl_tp()` retorna dict indexado por symbol | 3 trades OPEN → dict com 3 keys | Média |

### 7.2 Arquivos de Teste

```text
tests/
└── api/
    ├── test_trade_history.py       (TEST_016_01 a TEST_016_04, TEST_016_12)
    ├── test_bot_activity.py        (TEST_016_05 a TEST_016_09)
    └── test_positions_sl_tp.py     (TEST_016_10, TEST_016_11, TEST_016_13)
```

### 7.3 Evidências Requeridas na PR

- [ ] `pytest tests/ --tb=short -q` com todas as 13+ asserções passando
- [ ] `ruff check src/ tests/` sem erros
- [ ] Descrição textual ou screenshot do painel mostrando: indicador de saúde ativo,
      colunas SL/TP preenchidas, tabela de histórico com pelo menos 1 trade, filtros funcionando
- [ ] Referência às seções desta SPEC impactadas no corpo da PR

---

## 8. Tratamento de Erros

| Erro / Condição | Causa | Ação do Sistema |
|---|---|---|
| MongoDB indisponível em `GET /trades/history` | Container down | Retorna 503 com `{"detail": "Repositório indisponível"}` |
| MongoDB indisponível em `GET /bot-activity` | Container down | Retorna 200 com `status: "inactive"`, `last_activity_at: null` |
| Falha ao enriquecer posições com SL/TP | Erro na query MongoDB | Posições retornadas com `sl_price: null`, `tp_price: null`; log warning |
| Exception em `fetchBotActivity()` no frontend | API offline | catch silencioso; badge permanece no último estado conhecido |
| Exception em `fetchTradeHistory()` no frontend | API offline | catch silencioso; tabela permanece com dados anteriores |
| `pnl_usdt` nulo em trade fechado | Trade sem PnL calculado | Campo retornado como `null`; frontend exibe "—" |
| `closed_at` nulo em trade fechado | Dado inconsistente no MongoDB | Campo retornado como `null`; frontend exibe "—"; não quebra a tabela |
| Collections `signals` e `audit` ambas vazias | Bot nunca executou ciclo | `GET /bot-activity` retorna `status: "inactive"`, sem erro |

---

## 9. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Cruzamento posição-trade por symbol falhar se bot operar >1 posição por símbolo | Médio — SL/TP errado exibido | Invariante existente (SPEC_001) já proíbe isso; documentar como pré-condição |
| `generation_time` do ObjectId impreciso em documentos importados/migrados | Baixo — inatividade falsa | Aceitar: contexto é operação normal do bot, não dados migrados |
| Polling de 30s no indicador de saúde aumentar carga | Baixo — 2 req/min | Carga irrelevante; query usa índice primário `_id` |
| Tabela de histórico lenta sem índice adequado | Médio — timeout no frontend | Garantir índice em `{status: 1, closed_at: -1}` na collection `trades` (Task 1 do plano) |
| Filtros no frontend resetam ao atualizar via WebSocket | Baixo — UX levemente perturbador | Documentado como comportamento esperado em AC-06 da US-016-04 |

---

## 10. Definição de Pronto (DoD Global)

- [ ] SPEC aprovada pelo Time A
- [x] US-016-01: Colunas SL/TP visíveis na tabela de posições (endpoint enriquecido + frontend)
- [x] US-016-02: Endpoint `GET /trades/history` implementado com testes passando
- [x] US-016-03: Endpoint `GET /bot-activity` implementado com badge no frontend
- [x] US-016-04: Filtros de símbolo e direção funcionando no frontend
- [x] Nenhuma invariante da seção 6.1 violada em nenhum cenário de teste
- [ ] `pytest tests/ --tb=short -q` com 100% das asserções críticas passando
- [ ] `ruff check src/ tests/` sem erros
- [ ] `docs/SDD/README.md` atualizado com SPEC_016 (status: Concluída após DoD)
- [ ] Rastreabilidade PRD → SPEC_016 → Teste → Código comprovada na PR

---

## 11. Plano de Entrega — Task Graph Sugerido

| Task | Descrição | Dependências |
|---|---|---|
| T1 | Adicionar índice `{status: 1, closed_at: -1}` na collection `trades` | — |
| T2 | Implementar `get_trade_history()` e `get_open_trade_sl_tp()` no `MongoRepository` | T1 |
| T3 | Criar `src/api/routes/trades.py` com `GET /trades/history` | T2 |
| T4 | Adicionar `GET /bot-activity` em `src/api/routes/health.py` | T2 |
| T5 | Estender `GET /positions` para enriquecer com SL/TP do MongoDB | T2 |
| T6 | Registrar router `trades` em `src/api/main.py` | T3 |
| T7 | Implementar filtros de posição no `app.js` (frontend) | T5 |
| T8 | Implementar histórico de trades no `app.js` e `index.html` | T3, T6 |
| T9 | Implementar indicador de saúde do bot no `app.js` e `index.html` | T4 |
| T10 | Implementar testes unitários (13 testes em 3 arquivos) | T2, T3, T4, T5 |

---

## Histórico

- **2026-05-06:** Criação da SPEC_016 pelo Time A. Status: Em Refinamento.
- **2026-05-06:** Implementação dos objetivos OBJ-01..OBJ-04 no backend/frontend e adição dos testes TEST_016_01..TEST_016_13. Status: Em Execução (aguardando evidências finais de PR/DoD global).
