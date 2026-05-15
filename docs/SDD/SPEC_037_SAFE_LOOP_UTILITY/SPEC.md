# SPEC_037 — Extração de `safe_loop` Utility

**ID:** SPEC_037
**Status:** Rascunho
**Data:** 2026-05-11
**Versão:** 1.0
**Dependências:** Nenhuma
**Skill de validação:** `sdd-spec-driven-development`, `qa-review`

---

## 1. Título e Resumo

### 1.1 Nome da Funcionalidade

Extração do padrão `safe_loop` para módulo `common/loops.py`

### 1.2 Resumo

**O que é:** Uma função utilitária assíncrona que encapsula o padrão repetitivo de loop infinito com tratamento de `CancelledError`, log de exceções e sleep entre iterações — eliminando boilerplate nos loops periódicos que compartilham o mesmo contrato operacional.

**Por que estamos fazendo:** O padrão `while True: try: ... except CancelledError: return except Exception: log + sleep` aparece em vários loops periódicos com pequenas variações. Cada nova task que precisa de um loop com contrato equivalente replica o mesmo boilerplate. Extrair para um utilitário reduz duplicação, garante tratamento de erro consistente e acelera desenvolvimento.

**Valor de negócio:** Reduz uma quantidade relevante de boilerplate repetido, garante consistência no tratamento de erros e reduz a superfície de bugs em novos loops.

**Conexão com PRD/SPEC:** Refatoração técnica transversal — aplica-se a todos os módulos com loops de monitoramento.

---

## 2. Objetivos e Escopo

### 2.1 Objetivos

- [ ] Criar `common/loops.py` com função `safe_loop()` para loops assíncronos de cadência fixa
- [ ] Refatorar os módulos compatíveis com o contrato do utilitário
- [ ] Zero mudança de comportamento em runtime
- [ ] Testes unitários para o utilitário

### 2.2 Fora do Escopo

- **Não inclui:** Mudança na lógica de intervalo ou heartbeat — cada caller mantém controle do intervalo
- **Não inclui:** Mudança na estratégia de logging — cada caller fornece seu logger
- **Não inclui:** `BackupTask` com agendamento dinâmico para horário específico
- **Não inclui:** `_health_server()` e outros servidores/lifecycles que não são loops periódicos de iteração fixa
- **Não inclui:** loops com “primeira execução atrasada” como contrato primário, a menos que sejam adaptados explicitamente por um wrapper do caller

---

## 3. Referências

| Documento | Seção | Relevância |
|---|---|---|
| `docs/SDD/SPEC.md` | §7.2 | Padrão de loops de monitoramento |
| `SPEC_007/SPEC.md` | — | Resiliência e continuidade operacional |

---

## 4. Histórias de Usuário e Requisitos

### US-037-01: Função `safe_loop` para iterações assíncronas

> Como **desenvolvedor**, quero **invocar `safe_loop(iteration_fn, interval, logger, error_event)`** para **executar um loop periódico assíncrono com tratamento consistente de erros**.

**Critérios de Aceitação:**

```text
DADO   um módulo com um loop periódico simples
QUANDO safe_loop() é invocada com iteration_fn que retorna normalmente
ENTÃO  iteration_fn é chamada a cada `interval` segundos
```

```text
DADO   um módulo com um loop que lança exceção
QUANDO a exceção ocorre na iteration 5
ENTÃO  o erro é logado com error_event e o loop continua na iteration 6
```

```text
DADO   uma tarefa com safe_loop em execução
QUANDO CancelledError é lançado
ENTÃO  a função retorna imediatamente sem propagar o erro
```

- [ ] AC-01: iteration_fn é chamada repetidamente com intervalo respeitado
- [ ] AC-02: Exceções são logadas sem interromper o loop
- [ ] AC-03: CancelledError interrompe o loop silenciosamente

### US-037-02: Refatoração dos loops compatíveis

> Como **desenvolvedor**, quero **substituir o boilerplate manual dos loops compatíveis por `safe_loop()`** para **reduzir duplicação e garantir tratamento consistente**.

**Módulos afetados:**

| Módulo | Arquivo | Linhas de boilerplate | Função atual |
|---|---|---|---|
| HeartbeatTask | `src/main.py:142-150` | ~9 | `run()` |
| RuntimeMonitorSyncTask | `src/main.py:462-471` | ~11 | `run()` |
| TradingMonitor | `src/main.py:577-595` | ~11 | `run()` |
| OrderMonitor | `src/monitoring/order_monitor.py:115-138` | ~15 | `run()` |

- [ ] AC-01: Todos os loops compatíveis usam `safe_loop()` após refatoração
- [ ] AC-02: Comportamento idêntico verificado por testes existentes

**Loops explicitamente excluídos desta refatoração:**

- `PerformanceReporter` — primeira execução é atrasada por contrato; requer adaptação explícita se vier a usar o helper
- `BackupTask` — agendamento dinâmico em horário específico, não é loop de cadência fixa
- `_health_server()` — lifecycle de servidor, não loop periódico de iteração fixa

---

## 5. Design e Arquitetura

### 5.1 Módulo `common/loops.py`

```python
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any


async def safe_loop(
    iteration_fn: Callable[[], Awaitable[Any]],
    *,
    interval: float,
    logger: Any,
    error_event: str = "safe_loop_error",
    loop_name: str | None = None,
    on_start: Callable[[], Awaitable[Any]] | None = None,
    on_stop: Callable[[], Awaitable[Any]] | None = None,
) -> None:
    """Executa iteration_fn em loop assíncrono com tratamento padronizado de erros.

    Args:
        iteration_fn: Coroutine chamada a cada iteração.
        interval: Segundos entre o fim de uma iteração e o início da próxima.
        logger: Instância de logger estruturado (structlog).
        error_event: Nome do evento de log em caso de erro.
        loop_name: Identificador opcional para logs.
        on_start: Coroutine opcional executada antes do loop.
        on_stop: Coroutine opcional executada após o loop (cleanup).

    Exceptions:
        CancelledError: interrompe o loop silenciosamente.
        Qualquer outra: logada via logger.error com error_event,
                         o loop continua na próxima iteração.
    """
    if on_start is not None:
        await on_start()

    while True:
        try:
            await iteration_fn()
        except asyncio.CancelledError:
            if on_stop is not None:
                await on_stop()
            return
        except Exception as exc:
            logger.error(
                error_event,
                loop_name=loop_name,
                error_type=type(exc).__name__,
                exc_info=True,
            )
        await asyncio.sleep(interval)
```

### 5.2 Interfaces

**Entradas:**

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `iteration_fn` | `Callable[[], Awaitable[Any]]` | Sim | Coroutine de cada iteração |
| `interval` | `float` | Sim | Intervalo em segundos |
| `logger` | `Any` (structlog) | Sim | Logger para eventos |
| `error_event` | `str` | Não | Nome do evento de erro (default `"safe_loop_error"`) |
| `loop_name` | `str \| None` | Não | Identificador para logs |
| `on_start` | opcional | Não | Hook executado antes do loop |
| `on_stop` | opcional | Não | Hook executado no cancelamento |

**Saída:** `None` — a função executa até ser cancelada.

**Contrato dos hooks:**

- `on_start`: se falhar, a exceção é propagada e o loop não inicia
- `on_stop`: se falhar durante cancelamento, a falha é logada e suprimida para preservar shutdown gracioso

### 5.3 Fluxo de Dados / Sequência

```mermaid
sequenceDiagram
    participant Caller as Caller (ex: RuntimeMonitorSyncTask)
    participant Loop as safe_loop()
    participant Fn as iteration_fn

    Caller->>Loop: safe_loop(fn, interval=30)
    Loop->>Fn: await fn()
    Fn-->>Loop: ok / exception
    Note over Loop: log se exception
    Loop->>Loop: await asyncio.sleep(30)
    Loop->>Fn: await fn()
    Fn-->>Loop: ok
    Note over Loop: CancelledError → return
```

---

## 6. Regras de Negócio e Restrições

### 6.1 Invariantes

| ID | Invariante | Violação → Ação |
|---|---|---|
| INV-037-01 | `interval > 0` | `ValueError` na inicialização |
| INV-037-02 | `iteration_fn` nunca é chamada concorrentemente | Garantido por `await` sequencial |
| INV-037-03 | Exceções em `on_stop` não interrompem o shutdown | Log + continue |
| INV-037-04 | `on_start` falha antes de entrar no loop | Propaga exceção e impede início |

### 6.2 Padrões de Segurança

- `exc_info=True` apenas em erros inesperados (não em `CancelledError`)
- `error_event` deve seguir nomenclatura snake_case do projeto

---

## 7. Testes e Validação

### 7.1 Testes Unitários

| ID | Descrição | Cenário | Prioridade |
|---|---|---|---|
| TEST-037-01 | Loop executa N iterações com intervalo respeitado | iteration_fn conta chamadas | Alta |
| TEST-037-02 | Exceção em iteration_fn não interrompe loop | mock que lança uma vez, depois ok | Alta |
| TEST-037-03 | CancelledError interrompe loop | cancelar task após 2 iterações | Alta |
| TEST-037-04 | on_start executado antes da primeira iteração | mock verifica ordem | Média |
| TEST-037-05 | on_stop executado após cancelamento | mock verifica | Média |

### 7.2 Evidências Requeridas na PR

- [ ] `pytest tests/common/` passando
- [ ] Nenhum teste existente quebrado nos módulos compatíveis com o contrato de `safe_loop()`

---

## 8. Tratamento de Erros

| Erro / Condição | Causa | Ação do Sistema |
|---|---|---|
| `CancelledError` | Shutdown do bot | Retorna imediatamente, executa `on_stop` |
| Qualquer `Exception` | Erro interno da iteração | Loga com `error_event` + `exc_info=True`, continua |
| `iteration_fn` infinitamente lenta | Erro de design | Não tratado — responsabilidade do caller |
| `on_start` falha | Erro de inicialização | Propaga exceção e aborta o loop |
| `on_stop` falha | Erro de cleanup | Loga e suprime a falha para não quebrar shutdown |

---

## 9. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Mudança silenciosa de comportamento | Médio | Testes existentes devem passar sem alteração |
| Um módulo tem pattern diferente demais | Baixo | Manter o loop específico no caller ou criar um wrapper adaptador explícito |

---

## 10. Definição de Pronto (DoD)

- [ ] `common/loops.py` criado com `safe_loop()` e cobertura de testes > 90%
- [ ] Apenas os módulos com contrato compatível foram refatorados para `safe_loop()`
- [ ] `pytest` suite completa passando
- [ ] Zero mudança de comportamento verificada por CI

---

## Histórico

- **2026-05-11:** Criação da SPEC_037.
