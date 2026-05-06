# SPEC_012 — Monitoramento Ativo de Ordens e Posições Abertas

**ID:** SPEC_012
**Status:** Em Execução
**Data:** 2026-05-05
**Autor:** Time A (Refinamento)
**Executores:** Time B (Execução)
**Skills requeridas:** Python, asyncio, ccxt, motor, structlog, pytest
**Depende de:** SPEC_001, SPEC_004, SPEC_007, SPEC_008

---

## 1. Título e Resumo

### 1.1 Nome da Funcionalidade

Monitoramento Ativo de Ordens e Posições Abertas.

### 1.2 Resumo (High-Level Definition)

**O que é:** Task assíncrona independente (`OrderMonitor`) que inspeciona, a cada 60 segundos, o estado das ordens SL/TP e posições abertas registradas no MongoDB, detectando e tratando quatro cenários operacionais: TP executado, SL executado, SL cancelado (posição sem proteção), e fechamento manual de posição.

**Por que estamos fazendo:** O bot abre trades e coloca ordens de proteção, mas não há mecanismo que detecte automaticamente o encerramento dessas posições. Isso significa que o MongoDB pode ficar com trades no status `OPEN` indefinidamente mesmo após a posição ter sido encerrada, gerando inconsistências nos relatórios de performance e impedindo abertura de novas posições no mesmo símbolo.

**Valor de negócio:** Garante que o estado do MongoDB reflita sempre a realidade da exchange; permite cálculo correto de PnL; previne bloqueios desnecessários na abertura de novas posições; e alerta o operador imediatamente quando uma posição fica desprotegida.

**Conexão com PRD/SPEC:** PRD §MVP item 4 — "Proteção de todas as posições abertas"; SPEC_007 §9 — "Trade ACTIVE órfão no MongoDB" como risco a mitigar em SPEC futura.

---

## 2. Objetivos e Escopo

### 2.1 Objetivos (o que será entregue)

- [ ] `OrderMonitor`: task assíncrona em loop de 60s, padrão `PerformanceReporter`
- [ ] Detecção e registro de TP executado: PnL real via `fetch_order`
- [ ] Detecção e registro de SL executado: PnL real via `fetch_order`
- [ ] Alerta crítico via Telegram quando SL cancelado com posição aberta
- [ ] Detecção de fechamento manual: cancelar ordens remanescentes, is_estimated=True
- [ ] Retry com backoff exponencial em `fetch_order` (padrão SPEC_007)
- [ ] Guard de notificação duplicada por trade_id em memória
- [ ] Shutdown gracioso via `asyncio.CancelledError`
- [ ] 13+ testes unitários cobrindo todos os cenários

### 2.2 Fora do Escopo (Non-Goals)

- **Não inclui:** Recolocação automática de SL cancelado (decisão DD-002: operador decide)
- **Não inclui:** WebSocket para monitoramento em tempo real (polling 60s é suficiente)
- **Não inclui:** Monitoramento de margens ou chamadas de margem
- **Não inclui:** Notificações por canal diferente do Telegram configurado
- **Não inclui:** Histórico persistente de eventos de monitoramento (apenas audit log)

---

## 3. Referências

| Documento | Seção | Relevância |
|---|---|---|
| `SPEC_007` | §5.1, §6.4 | Padrão de retry com backoff exponencial e logs seguros |
| `SPEC_004` | §4, §7.1 | Padrão de notificação Telegram e eventos críticos |
| `SPEC_008` | §5 | Padrão de task assíncrona periódica (PerformanceReporter) |
| `src/exchange/binance_client.py` | `fetch_ohlcv_with_retry` | Template de retry |
| `src/notifications/performance_reporter.py` | `run()` | Padrão de loop periódico |
| `src/storage/repository.py` | `update_trade_status` | Contrato de atualização |

---

## 4. Histórias de Usuário e Requisitos

### US-012-01: TP Executado — Registrar PnL Real

> Como **operador**, quero que o MongoDB seja atualizado automaticamente com o status CLOSED_TP e o PnL real quando um Take Profit for executado.

**Critérios de Aceitação:**

```text
DADO   que um trade OPEN existe no MongoDB com tp_order_id
QUANDO a ordem TP é preenchida na exchange (status=closed)
ENTÃO  o sistema faz fetch_order(tp_order_id) para obter exit_price real (campo `average`)
E      calcula PnL: (exit_price - entry_price) * quantity * side_multiplier - fees
E      atualiza MongoDB: status=CLOSED_TP, exit_price, pnl_usdt, closed_at
E      registra evento no audit log
```

- [ ] AC-01: `exit_price` = campo `average` da ordem (não `stopPrice`)
- [ ] AC-02: `pnl_usdt` calculado com slippage real
- [ ] AC-03: `closed_at` = `datetime.now(UTC)` no momento da detecção

---

### US-012-02: SL Executado — Registrar PnL Real

> Como **operador**, quero que o MongoDB reflita o fechamento via Stop Loss com o PnL real.

**Critérios de Aceitação:**

```text
DADO   que um trade OPEN existe no MongoDB com sl_order_id
QUANDO a ordem SL é preenchida na exchange (status=closed)
ENTÃO  o sistema faz fetch_order(sl_order_id) para obter exit_price real
E      calcula PnL (normalmente negativo)
E      atualiza MongoDB: status=CLOSED_SL, exit_price, pnl_usdt, closed_at
```

- [ ] AC-01: `exit_price` = `average` da ordem SL (reflete slippage real)
- [ ] AC-02: `pnl_usdt` negativo para losses — aritmética correta para LONG e SHORT

---

### US-012-03: SL Cancelado — Alerta Crítico

> Como **operador**, quero receber alerta imediato quando uma posição aberta perder a proteção de stop loss.

**Critérios de Aceitação:**

```text
DADO   que um trade OPEN existe no MongoDB
E      a posição ainda existe na exchange (contratos > 0)
QUANDO a ordem SL está cancelada ou não existe mais
ENTÃO  o sistema envia notificação Telegram com severidade CRITICAL
E      a mensagem contém: símbolo, sl_price, current_price, pct_distance
E      a notificação é enviada apenas uma vez por trade_id (guard de duplicata)
```

- [ ] AC-01: `pct_distance = abs(current_price - sl_price) / sl_price * 100`
- [ ] AC-02: Guard `_notified_sl_missing: set[str]` previne spam
- [ ] AC-03: Se posição não existe mais → não alerta (posição já fechada)

---

### US-012-04: Fechamento Manual — Cancelar Ordens Remanescentes

> Como **operador**, quero que o bot limpe automaticamente ordens abertas quando eu fechar uma posição manualmente.

**Critérios de Aceitação:**

```text
DADO   que um trade OPEN existe no MongoDB
QUANDO a posição na exchange = 0 (fechada manualmente)
E      ainda existem ordens SL/TP abertas
ENTÃO  o sistema cancela todas as ordens do símbolo
E      obtém exit_price via fetch_ticker (preço estimado)
E      atualiza MongoDB: status=CLOSED_MANUAL, exit_price, is_estimated=True
```

- [ ] AC-01: `is_estimated=True` sinaliza que exit_price não é o preço real de execução
- [ ] AC-02: `cancel_all_orders` chamado antes de atualizar status
- [ ] AC-03: PnL calculado com exit_price estimado

---

## 5. Design e Arquitetura

### 5.1 Novo Módulo: `src/monitoring/order_monitor.py`

```
src/
└── monitoring/
    ├── __init__.py          (existente — logger)
    └── order_monitor.py     (novo)
```

### 5.2 Classe OrderMonitor

```python
class OrderMonitor:
    def __init__(
        self,
        client: BinanceClient,
        repository: MongoRepository,
        notifier: Notifier,
        interval_seconds: int = 60,
    ) -> None: ...

    async def run(self) -> None:
        """Loop infinito com intervalo de 60s. Trata CancelledError graciosamente."""

    async def _check_all_open_trades(self) -> None:
        """Itera trades OPEN do MongoDB e delega para _check_trade."""

    async def _check_trade(self, trade: dict) -> None:
        """Verifica estado de um único trade na exchange."""

    async def _handle_tp_executed(self, trade: dict, order: dict) -> None: ...
    async def _handle_sl_executed(self, trade: dict, order: dict) -> None: ...
    async def _handle_sl_missing(self, trade: dict, current_price: float) -> None: ...
    async def _handle_manual_close(self, trade: dict) -> None: ...
    async def _fetch_order_with_retry(self, order_id: str, symbol: str) -> dict | None: ...
    def _calc_pnl(self, trade: dict, exit_price: float) -> float: ...
```

### 5.3 Novo Método em BinanceClient: `fetch_order`

```python
async def fetch_order(self, order_id: str, symbol: str) -> dict:
    """Busca detalhes de uma ordem pelo ID.

    Retorna o objeto de ordem ccxt, incluindo o campo `average`
    que representa o preço médio de execução real.
    Nunca loga str(exc) — usa type(exc).__name__.
    """
```

### 5.4 Novo Evento de Notificação: `SLMissingEvent`

Adicionado em `src/notifications/events.py`:

```python
@dataclass(frozen=True)
class SLMissingEvent:
    symbol: str
    trade_id: str
    sl_price: float
    current_price: float
    pct_distance: float
    timestamp: datetime
```

E novo tipo em `NotificationEvent`:

```python
SL_MISSING = "sl_missing"
```

### 5.5 Fluxo de Verificação por Trade

```
Para cada trade OPEN no MongoDB:
    1. fetch_order(sl_order_id) → cancelado? → _handle_sl_missing
    2. fetch_order(sl_order_id) → fechado? → _handle_sl_executed
    3. fetch_order(tp_order_id) → fechado? → _handle_tp_executed
    4. fetch_open_positions(symbol) → 0? → _handle_manual_close
```

### 5.6 Integração em `src/main.py`

Segue o padrão do `PerformanceReporter`:

```python
order_monitor = OrderMonitor(
    client=client,
    repository=repo,
    notifier=notifier,
)
tasks.append(asyncio.create_task(order_monitor.run()))
```

### 5.7 Cálculo de PnL

```python
def _calc_pnl(self, trade: dict, exit_price: float) -> float:
    direction = trade["direction"]  # "long" ou "short"
    entry = trade["entry_price"]
    qty = trade["quantity"]
    fees = trade.get("fees", 0.0)
    side_mult = 1.0 if direction == "long" else -1.0
    return (exit_price - entry) * qty * side_mult - fees
```

---

## 6. Requisitos Funcionais Detalhados

| ID | Descrição | Prioridade |
|---|---|---|
| RF-001 | Detectar SL cancelado + posição aberta → Telegram CRITICAL | Alta |
| RF-002 | Detectar TP executado → fetch_order → CLOSED_TP | Alta |
| RF-003 | Detectar SL executado → fetch_order → CLOSED_SL | Alta |
| RF-004 | Detectar fechamento manual → cancel_all + CLOSED_MANUAL | Alta |
| RF-005 | Guard de notificação duplicada (set em memória) | Alta |
| RF-006 | Retry 3x com backoff em fetch_order | Alta |
| RF-007 | Falha em um símbolo não afeta outros | Alta |
| RF-008 | Shutdown gracioso ao receber CancelledError | Alta |
| RF-009 | Audit log para todo evento de encerramento | Média |
| RF-010 | Ciclo de 60s configurável via parâmetro | Baixa |
| RF-011 | Logs seguros: type(exc).__name__, nunca str(exc) | Alta |
| RF-012 | is_estimated=True para exit_price via fetch_ticker | Alta |

---

## 7. Decisões de Design

| ID | Decisão | Justificativa |
|---|---|---|
| DD-001 | Polling 60s (sem WebSocket) | Suficiente para perfil de trading; simples e robusto |
| DD-002 | SEM recolocação automática de SL | Decisão do operador; bot apenas alerta |
| DD-003 | Guard de duplicata em memória (não persistido) | Evita spam sem complexidade de estado persistente; aceita falso alerta em restart |
| DD-004 | exit_price = `average` (não `price` ou `stopPrice`) | `average` reflete slippage real de execução |
| DD-005 | is_estimated=True para fechamento manual | Sinaliza que PnL calculado é aproximação |

---

## 8. Regras de Negócio e Invariantes

| ID | Invariante | Violação → Ação |
|---|---|---|
| INV-012-01 | Toda posição aberta deve ter SL monitorado | Detectar e alertar imediatamente |
| INV-012-02 | Nenhuma ordem remanescente após fechamento manual | `cancel_all_orders` obrigatório |
| INV-012-03 | Logs de monitoring nunca expõem credenciais | `type(exc).__name__` exclusivamente |
| INV-012-04 | Guard de notificação duplicada ativo por toda a vida do processo | Set `_notified_sl_missing` nunca é limpado |

---

## 9. Tratamento de Erros

| Erro / Condição | Causa | Ação do Sistema |
|---|---|---|
| `ccxt.NetworkError` em `fetch_order` | Falha de rede temporária | retry×3 com backoff 1s, 2s, 4s |
| `ccxt.OrderNotFound` em `fetch_order` | Ordem não existe na exchange | log warning, assume SL missing se era SL |
| Falha ao cancelar ordens no fechamento manual | Erro na exchange | log error, atualiza status mesmo assim |
| MongoDB inacessível em `get_open_trades` | Container down | log error, aguarda próximo ciclo |
| Falha ao enviar notificação Telegram | Rede ou token inválido | log warning, não bloqueia |
| Exceção em `_check_trade` para um símbolo | Qualquer erro | log error, continua para próximo trade |

---

## 10. Testes e Validação

| ID | Descrição | Cenário |
|---|---|---|
| TEST_012_01 | SL cancelado → notificação critical | sl_order status=canceled, posição aberta |
| TEST_012_02 | Sem notificação duplicada | segundo ciclo com mesmo trade_id |
| TEST_012_03 | TP executado → PnL correto no MongoDB | tp_order status=closed, average=real |
| TEST_012_04 | SL executado → PnL correto no MongoDB | sl_order status=closed, average=real |
| TEST_012_05 | Fechamento manual → cancel_all + CLOSED_MANUAL + is_estimated=True | posição=0, ordens abertas |
| TEST_012_06 | fetch_order retry (NetworkError → sucesso no retry) | 1 falha + 1 sucesso |
| TEST_012_07 | fetch_order esgota retries → log warning, aguarda próximo ciclo | 3 falhas |
| TEST_012_08 | Falha em um símbolo não afeta outros | exceção isolada |
| TEST_012_09 | Startup reconciliation (trade OPEN com SL preenchido) | estado consistente ao iniciar |
| TEST_012_10 | Shutdown gracioso (CancelledError) | task.cancel() |
| TEST_012_11 | PnL com fees | fees > 0 deduzidos do PnL |
| TEST_012_12 | PnL sem fees | fees = 0 |
| TEST_012_13 | Slippage no SL (exit_price = average, não stop_price) | average != stopPrice |

---

## 11. Definição de Pronto (DoD Global)

- [ ] `src/monitoring/order_monitor.py` implementado e passando em todos os testes
- [ ] `fetch_order` adicionado ao `BinanceClient` com retry
- [ ] `SLMissingEvent` e `NotificationEvent.SL_MISSING` adicionados
- [ ] `OrderMonitor` integrado em `src/main.py`
- [ ] 13 testes em `tests/monitoring/test_order_monitor.py` passando
- [ ] `docs/SDD/README.md` atualizado com SPEC_012
- [ ] `ruff check src/ tests/` sem erros
- [ ] Nenhuma invariante da seção 8 violada

---

## Histórico

- **2026-05-05:** Criação da SPEC_012 pelo Time A. Implementação pelo Time B.
