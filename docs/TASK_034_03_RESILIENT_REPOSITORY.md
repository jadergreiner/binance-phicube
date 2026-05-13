# TASK_034_03: ResilientMongoRepository

## Visão Geral

`ResilientMongoRepository` é uma Facade que wrappea `MongoRepository` com capacidades de:
- **Circuit Breaker**: Pausa tentativas quando o MongoDB está indisponível
- **Retry com Backoff**: 3 tentativas com delays exponenciais (100ms, 200ms, 400ms)
- **Graceful Degrade**: Diferentes estratégias por criticidade (Tipo B vs Tipo C)
- **Journal Local**: Persiste trades não-persistidos em arquivo `.jsonl` para reprocessamento

## Implementação

### Arquivo Principal
- `src/storage/resilient_repository.py` — Facade + Circuit Breaker + Retry + Journal

### Configuração (settings.py)
- `circuit_breaker_mongo_recovery_timeout_secs: int = 60` — Timeout de recovery do CB

## Padrão de Criticidade

### Tipo B: Crítico (Retry 3x + Alert)
- `save_trade()` — Operações de trade (nunca perdem dados)
- `audit_log()` — Registros de auditoria
- `insert_one()` — Inserts genéricos

**Comportamento:**
- Tenta 3x com backoff (100ms, 200ms, 400ms)
- Se falha 3x: journala em `PendingTradesJournal` (para `save_trade`)
- Envia Telegram alert em caso de falha final
- **Nunca levanta exceção** — sempre retorna `None` ou `doc_id`

### Tipo C: Não-Crítico (Graceful Degrade)
- `save_signal()` — Sinais (podem ser recalculados)

**Comportamento:**
- Tenta 1x apenas
- Se falha: retorna `None` silenciosamente
- Sem alert, sem retry

## Uso

### Inicialização

```python
from src.storage.repository import MongoRepository
from src.storage.resilient_repository import ResilientMongoRepository
from src.notifications.telegram_notifier import TelegramNotifier
from src.resilience.circuit_breaker import CircuitBreakerRegistry

# Cria MongoRepository
mongo_repo = MongoRepository(
    uri="mongodb://mongo:27017",
    database="phicube"
)

# Cria notifier (Telegram)
notifier = TelegramNotifier(token="...", chat_id="...")

# Cria CircuitBreakerRegistry (opcional, default: novo com namespace='mongodb')
cb_registry = CircuitBreakerRegistry(namespace="mongodb")

# Wrappea com ResilientMongoRepository
resilient_repo = ResilientMongoRepository(
    real_repo=mongo_repo,
    notifier=notifier,
    cb_registry=cb_registry,
    recovery_timeout_secs=60,  # default: 60
)
```

### Exemplo de Uso

```python
# Tipo B: save_trade com retry 3x
trade = ...
doc_id = await resilient_repo.save_trade(trade)
# Se falha 3x:
#   - Journala em PendingTradesJournal
#   - Envia alert Telegram
#   - Retorna None (nunca exceção)

# Tipo C: save_signal com graceful degrade
signal_dict = {...}
signal_id = await resilient_repo.save_signal(signal_dict)
# Se falha:
#   - Retorna None
#   - Sem retry, sem alert

# Tipo B: audit_log com retry 3x
await resilient_repo.audit_log("trade_opened", {"trade_id": "123"})
# Se falha 3x: envia alert Telegram

# Tipo B: insert_one genérico
doc_id = await resilient_repo.insert_one("customers", {"name": "Alice"})
```

## Circuit Breaker

### Estados
- **CLOSED** (normal): Tenta operação
- **OPEN** (falhas detectadas): Não tenta, retorna None/journala
- **HALF_OPEN** (em recuperação): Tenta uma vez após timeout

### Transição
```
CLOSED --[3 falhas]--> OPEN --[timeout expirado]--> HALF_OPEN
                                                        |
                                            sucesso -> CLOSED
                                            falha -----> OPEN
```

### Timeouts
- `recovery_timeout_secs=60` — Tempo de espera antes de tentar HALF_OPEN
- Configurável via `CIRCUIT_BREAKER_MONGO_RECOVERY_TIMEOUT_SECS` em `.env`

## PendingTradesJournal

Arquivo local `.jsonl` em `src/storage/.pending_trades.jsonl` que:
- Persiste trades não-persistidos no MongoDB
- Garante idempotência (não duplica trades)
- Permite reprocessamento posterior

### Reprocessamento

```python
# Reprocess trades pendentes
reprocessed, failed = await journal.reprocess_pending_trades(resilient_repo)
logger.info(f"Reprocessados: {reprocessed}, Falharam: {failed}")
```

## Logging

Todos os eventos são registrados via `structlog`:

### Sucesso
```json
{"event": "save_trade_succeeded", "entry_order_id": "order_123", "attempt": 1}
```

### Retry
```json
{"event": "save_trade_attempt_failed", "entry_order_id": "order_123", "attempt": 2, "error": "TimeoutError"}
```

### Falha Final + Journaling
```json
{"event": "save_trade_failed_after_retries", "entry_order_id": "order_123", "attempts": 3, "last_error": "ConnectionError"}
{"event": "save_trade_journaled_after_failures", "entry_order_id": "order_123"}
```

### Circuit Breaker Aberto
```json
{"event": "save_trade_circuit_breaker_open", "cb_name": "mongodb:save_trade", "recovery_timeout_secs": 60}
{"event": "save_trade_journaled_due_to_open_cb", "entry_order_id": "order_123"}
```

## Métricas e Alertas

### Telegram Alerts
Enviados em caso de falha final (Tipo B):

```
🚨 **Erro ao salvar trade no MongoDB**
Entry Order ID: order_123
Símbolo: BTCUSDT
Tentativas: 3
Status: Journaled para reprocessamento
```

### Validações

#### Test Coverage: 77%
```
src/storage/resilient_repository.py   199   46   77%
```

#### Linhas Cobertas
- Todos os caminhos de retry (sucesso, falha, backoff)
- Journaling após falha 3x
- Graceful degrade (Tipo C)
- Circuit Breaker transitions
- Passthrough methods

#### Linhas Não Cobertas (23%)
- Linhas de `_send_alert` (notifier.send pode falhar silenciosamente)
- Alguns branches de except em passthrough methods

## Validação de Acceptance Criteria

✓ save_trade com CB aberto retenta 3x com backoff (100ms, 200ms, 400ms)
✓ save_trade falha 3x → journaled em PendingTradesJournal, retorna Ok
✓ save_signal com CB aberto retorna Ok (graceful degrade)
✓ audit_log retenta 3x; falha 3x → Telegram alert
✓ insert_one retenta 3x; genérico funciona
✓ PendingTradesJournal.add_trade() é chamado após 3ª falha de save_trade
✓ recovery_timeout_secs de 60s é respeitado
✓ Backoff: 100ms + 200ms + 400ms = 700ms total antes de abort
✓ Sem exceção levantada em save_trade (mesmo com todas as tentativas falhando)

## Testes

### Suite: tests/storage/test_resilient_repository.py
- 21 testes cobrindo:
  - Retry logic (sucesso, falha progressiva, 3 falhas)
  - Journaling (idempotência, fallback, reprocessamento)
  - Graceful degrade (Tipo C)
  - Audit log retry e alerts
  - insert_one genérico
  - Circuit Breaker integration
  - Passthrough methods

### Comando
```bash
pytest tests/storage/test_resilient_repository.py -v
```

## Segurança

### Dados Sensíveis
- ✓ DB credentials **não** são loggados (apenas collection names)
- ✓ Trade entry_order_id é loggado (necessário para rastreamento)
- ✓ Erros são capturados como `type(exc).__name__` (não a mensagem completa)

### Journal
- ✓ Arquivo `.pending_trades.jsonl` deve ter permissões restritas (600)
- ✓ Serialização segura via `json.dumps(default=str)`

## Integração Futura

### Pontos de Extensão
1. **Métricas**: Adicionar contadores de retry/circuit breaker abertos
2. **Observabilidade**: Integrar com Prometheus/Grafana
3. **Threshold Adaptativo**: Ajustar retry/timeout baseado em padrões de falha
4. **Multi-region**: Múltiplos Circuit Breakers para diferentes instâncias MongoDB

## Referências

- **SPEC_034**: Pipeline Pattern para Tick (TASK_034_03)
- **SPEC_007**: Resiliência e Recovery
- **CircuitBreaker**: `src/resilience/circuit_breaker.py`
- **PendingTradesJournal**: `src/storage/pending_trades_journal.py`
- **MongoRepository**: `src/storage/repository.py`
