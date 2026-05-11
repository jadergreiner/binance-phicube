# SPEC_034 — Recuperação Automática (Auto Recovery)

**ID:** SPEC_034
**Título:** Recuperação Automática: Circuit Breaker e Graceful Degradation
**Data:** 2026-05-10
**Status:** Rascunho
**Versão:** 1.0
**Dependências:** SPEC_007 (resiliência), SPEC_021 (validação operacional)
**PRD §:** Fase 1 — "Estabilidade operacional"

---

## 1. Objetivo

Atualmente o bot não tem recuperação automática — se uma chamada à API da Binance falha, se o MongoDB cai, ou se um módulo interno lança exceção, o erro propaga sem proteção.

Esta SPEC adiciona:
1. **Circuit Breaker** — para chamadas à exchange e MongoDB
2. **Graceful Degradation** — módulos não críticos falham sem derrubar o bot
3. **Reconexão automática** — MongoDB reconecta sem restart

---

## 2. Escopo

### Dentro do escopo
- Circuit breaker para `BinanceClient` (fetch_ohlcv, create_order, fetch_positions)
- Circuit breaker para `MongoRepository` (insert, find, update)
- Graceful degradation: se storage falha, bot loga warning e continua loop
- Reconexão automática: MongoDB driver (`motor`) já tem, mas precisa de configuração
- Healthcheck do bot reflete estado dos circuit breakers (OPEN/HALF_OPEN/CLOSED)
- Timeout configurável por chamada

### Fora do escopo
- Retry com backoff exponencial (já existe parcialmente)
- Fallback para cache local (será SPEC futura)
- Auto-restart do container via Docker (já tem `restart: unless-stopped`)

---

## 3. User Stories

### US-034-01 — Circuit breaker na exchange
**Como** operador,
**quero** que o bot não quebre se a Binance estiver instável,
**para** que trades em andamento não sejam abortados.

**Critério de aceite:**
- Após 3 falhas consecutivas de `fetch_ohlcv`, circuit breaker abre (OPEN)
- OPEN: chamadas falham rápido (fast fail) com `CircuitBreakerOpenError`
- Após 60s, transita para HALF_OPEN e tenta novamente
- Bem-sucedido → CLOSED. Falha → OPEN novamente
- Log: `"Circuit breaker [module.method] → OPEN"`

### US-034-02 — Graceful degradation
**Como** operador,
**quero** que o bot continue rodando mesmo se o MongoDB estiver offline,
**para** que sinais não parem de ser avaliados.

**Critério de aceite:**
- Falha de `repository.save_signal()` → log WARNING, loop continua
- Posições não são abertas sem storage (trade crítico requer persistência)
- Healthcheck retorna "degraded" quando storage offline

---

## 4. Modelo de Dados

### `CircuitBreakerState`

```python
from enum import Enum

class CircuitBreakerState(Enum):
    CLOSED = "closed"        # Normal: chamadas passam
    OPEN = "open"            # Falhando: chamadas falham rápido
    HALF_OPEN = "half_open"  # Testando: uma chamada passa
```

### Estado persistido (em memória)

```python
@dataclass
class CircuitBreaker:
    name: str
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0
    failure_threshold: int = 3       # Falhas consecutivas para OPEN
    recovery_timeout: float = 60.0   # Segundos até HALF_OPEN
    last_state_change: float = 0.0
```

---

## 5. Componentes

### 5.1 `src/resilience/circuit_breaker.py` — novo módulo

```python
class CircuitBreakerRegistry:
    """Gerencia todos os circuit breakers do sistema."""

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}

    def get(self, name: str, **kwargs) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name=name, **kwargs)
        return self._breakers[name]

    def state_summary(self) -> dict[str, str]:
        """Retorna {name: state} para healthcheck."""
        return {name: cb.state.value for name, cb in self._breakers.items()}
```

### 5.2 Decorator `@circuit_breaker`

```python
from functools import wraps
from typing import TypeVar, Callable, Awaitable

T = TypeVar("T")

def circuit_breaker(name: str, registry: CircuitBreakerRegistry):
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        cb = registry.get(name)
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            if cb.state == CircuitBreakerState.OPEN:
                if time.monotonic() - cb.last_state_change >= cb.recovery_timeout:
                    cb.state = CircuitBreakerState.HALF_OPEN
                else:
                    raise CircuitBreakerOpenError(f"Circuit breaker '{name}' is OPEN")
            try:
                result = await func(*args, **kwargs)
                if cb.state == CircuitBreakerState.HALF_OPEN:
                    cb.state = CircuitBreakerState.CLOSED
                    cb.failure_count = 0
                return result
            except Exception as e:
                cb.failure_count += 1
                cb.last_failure_time = time.monotonic()
                if cb.failure_count >= cb.failure_threshold:
                    cb.state = CircuitBreakerState.OPEN
                    cb.last_state_change = time.monotonic()
                raise
        return wrapper
    return decorator
```

### 5.3 Aplicação nos clientes

```python
# src/exchange/binance_client.py
class BinanceClient:
    @circuit_breaker("binance.fetch_ohlcv", registry)
    async def fetch_ohlcv(self, ...): ...

    @circuit_breaker("binance.create_order", registry)
    async def create_order(self, ...): ...

# src/storage/repository.py
class MongoRepository:
    @circuit_breaker("mongo.insert_one", registry)
    async def insert_one(self, ...): ...
```

### 5.4 Healthcheck estendido

```python
# src/api/routes/health.py
@router.get("/health")
async def health():
    cb_states = circuit_breaker_registry.state_summary()
    overall = "healthy"
    if any(s == "open" for s in cb_states.values()):
        overall = "degraded"
    return {"status": overall, "circuit_breakers": cb_states}
```

---

## 6. Invariantes

| ID | Invariante |
|----|-----------|
| INV-034-01 | Circuit breaker OPEN nunca deixa chamada real passar |
| INV-034-02 | `failure_count` zera após transição CLOSED bem-sucedida |
| INV-034-03 | Graceful degradation: storage falha não impede loop de trading |
| INV-034-04 | Ordem crítica (create_order) sempre tenta mesmo se CB aberto? → ❌ Não: CB aplica exceto para `create_order` que usa `@no_circuit_breaker` |

---

## 7. Testes

| ID | Descrição |
|----|-----------|
| TEST_034_01 | CB CLOSED → falha 3x → OPEN |
| TEST_034_02 | CB OPEN → chamada levanta `CircuitBreakerOpenError` |
| TEST_034_03 | CB HALF_OPEN → sucesso → CLOSED |
| TEST_034_04 | CB HALF_OPEN → falha → OPEN |
| TEST_034_05 | Storage falha → bot loga warning e continua |
| TEST_034_06 | CB state_summary reflete estados corretamente |
| TEST_034_07 | Decorator não afeta função sem falhas |

---

## 8. Arquivos

| Arquivo | Mudança |
|---------|---------|
| `src/resilience/__init__.py` | Criado |
| `src/resilience/circuit_breaker.py` | Criado — `CircuitBreaker`, `CircuitBreakerRegistry`, decorator |
| `src/resilience/exceptions.py` | Criado — `CircuitBreakerOpenError` |
| `src/exchange/binance_client.py` | Modificado — decorator `@circuit_breaker` |
| `src/storage/repository.py` | Modificado — decorator `@circuit_breaker` |
| `src/api/routes/health.py` | Modificado — incluir `circuit_breakers` na resposta |
| `tests/resilience/test_circuit_breaker.py` | Criado — TEST_034_01 a 07 |

---

## 9. Definition of Done

- [ ] `CircuitBreaker` com estados CLOSED/OPEN/HALF_OPEN
- [ ] Decorator `@circuit_breaker` funcional em funções async
- [ ] Aplicado em `BinanceClient.fetch_ohlcv` e `MongoRepository`
- [ ] Healthcheck reflete estado dos breakers
- [ ] Graceful degradation: storage falha não derruba o bot
- [ ] TEST_034_01 a 07 passando
- [ ] `ruff check src/ tests/` limpo
