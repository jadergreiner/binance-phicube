# SPEC_008 — Relatório Periódico de Performance via Telegram

**ID:** SPEC_008
**Status:** Concluída
**Data:** 2026-05-05
**Autor:** Time A (Refinamento)
**Executores:** Time B (Execução)
**Skills requeridas:** Python, asyncio, pytest, structlog
**Depende de:** SPEC_004, SPEC_006, SPEC_007
**Conexão PRD:** §Fase 2 linha 219, RF-10 (linha 169), RF-11 (linha 181), OKR Nível 3 linha 119

---

## 1. Título e Resumo

### 1.1 Nome da Funcionalidade

Relatório automático periódico de performance via Telegram

### 1.2 Resumo (High-Level Definition)

**O que é:** Um componente `PerformanceReporter` que executa como task assíncrona paralela ao bot,
calculando métricas agregadas de performance e enviando-as periodicamente via Telegram.

**Por que estamos fazendo:** O PRD §Fase 2 lista "Relatório automático periódico de performance via
Telegram" como primeira expansão pós-MVP. SPEC_004 entregou o canal Telegram e SPEC_006 entregou
as métricas — esta SPEC conecta os dois com agendamento automático.

**Valor de negócio:** O operador recebe visibilidade contínua de performance (win rate, P&L, RRR)
sem precisar consultar manualmente o endpoint `/performance`, reduzindo tempo de detecção de
degradação de estratégia.

**Conexão com PRD/SPEC:** PRD §Fase 2 linha 219 (extensão RF-10/RF-11).
OKR Nível 3 linha 119: "Relatórios de performance automáticos".

---

## 2. Objetivos e Escopo

### 2.1 Objetivos (o que será entregue)

- [x] Novo campo `PERFORMANCE_REPORT_INTERVAL_HOURS` no settings (0 = desabilitado)
- [x] Componente `PerformanceReporter` em `src/notifications/performance_reporter.py`
- [x] Integração no `_main()` de `src/main.py` como task paralela
- [x] Mensagem formatada com as 6 métricas do RF-11
- [x] Modo degradado: falha no MongoDB ou no Telegram não crasha o bot
- [x] 5 testes unitários cobrindo contratos de INV-008-01 a INV-008-04

### 2.2 Fora do Escopo (Non-Goals)

- **Não inclui:** Dashboard visual automático de performance (Fase 2 mais avançada)
- **Não inclui:** Relatório filtrado por período, símbolo ou timeframe
- **Não inclui:** Agendamento cron externo (o scheduler é interno ao processo do bot)
- **Não inclui:** Múltiplos canais de envio (apenas Telegram via `Notifier`)
- **Não inclui:** Backtesting ou análise histórica comparativa

---

## 3. Referências

| Documento | Seção | Relevância |
|---|---|---|
| `PRD.md` | §Fase 2 linha 219, RF-10/RF-11 | Requisito de origem |
| `docs/SDD/SPEC_004_.../SPEC.md` | Completo | `TelegramNotifier` e `Notifier` ABC |
| `docs/SDD/SPEC_006_.../SPEC.md` | Completo | `get_performance_metrics()` e métricas RF-11 |
| `src/notifications/notifier.py` | Interface `Notifier.send()` | Contrato de envio |
| `src/notifications/events.py` | `NotificationEvent` enum | Padrão de evento |
| `src/storage/repository.py` | `get_performance_metrics()` | Fonte de métricas |
| `src/config/settings.py` | `Settings` | Configuração de intervalo |
| `src/main.py` | `_main()` e `asyncio.gather()` | Ponto de integração |

---

## 4. User Stories

| ID | Como... | Quero... | Para... |
|---|---|---|---|
| US-008-01 | Operador | Receber relatório diário de performance no Telegram | Monitorar saúde da estratégia sem acessar terminal |
| US-008-02 | Operador | Configurar o intervalo do relatório via `.env` | Adaptar frequência ao meu workflow |
| US-008-03 | Operador | Desabilitar o relatório periódico quando necessário | Evitar spam em períodos de manutenção |
| US-008-04 | Operador | Que falha no Telegram não pare o bot | Garantir continuidade operacional |

---

## 5. Design e Arquitetura

### 5.1 Novo componente: `PerformanceReporter`

```
_main()
    ├─ TradingMonitor.run() [por símbolo/timeframe]
    └─ PerformanceReporter.run()  ← nova task paralela
           │
           ├─ asyncio.sleep(interval_hours * 3600)
           │
           └─ _send_report()
                  ├─ repository.get_performance_metrics()
                  ├─ _format_message(metrics)
                  └─ notifier.send(PERFORMANCE_REPORT, payload)
```

### 5.2 Contrato de interface

```python
class PerformanceReporter:
    def __init__(
        self,
        repository: MongoRepository,
        notifier: Notifier,
        interval_hours: float,
    ) -> None: ...

    async def run(self) -> None:
        """Loop infinito com sleep. Retorna imediatamente se interval_hours == 0."""

    async def _send_report(self) -> None:
        """Obtém métricas, formata mensagem, envia via notifier.send(). Nunca lança exceção."""
```

### 5.3 Evento de notificação

O relatório usa um novo evento `NotificationEvent.PERFORMANCE_REPORT` e um novo payload
`PerformanceReportEvent` com método `to_message()`. O `TelegramNotifier` já suporta qualquer
payload com `to_message()` pelo dispatch existente em `_format_message()`.

### 5.4 Configuração

```ini
# .env
PERFORMANCE_REPORT_INTERVAL_HOURS=24  # 0 = desabilitado; default: 24
```

---

## 6. Regras de Negócio e Invariantes

| ID | Invariante |
|---|---|
| INV-008-01 | Se `notifier` é `NullNotifier`, `_send_report()` é chamado mas não envia nada |
| INV-008-02 | Falha ao obter métricas do MongoDB → log `error_type=type(exc).__name__`, sem crash |
| INV-008-03 | Falha ao enviar Telegram → log warning, sem crash, aguarda próximo ciclo |
| INV-008-04 | `interval_hours == 0` → `run()` retorna imediatamente sem entrar no loop |

---

## 7. Testes

| ID | Cenário | Critério de Aceite |
|---|---|---|
| TEST_008_01 | `_send_report` com métricas válidas | Mensagem contém as 6 métricas formatadas; `notifier.send()` chamado |
| TEST_008_02 | `_send_report` com `total_trades == 0` | Mensagem simplificada enviada sem valores zerados confusos |
| TEST_008_03 | `_send_report` com MongoDB falhando | Não lança exceção; log de erro emitido |
| TEST_008_04 | `_send_report` com Telegram falhando | Não lança exceção; log de warning emitido |
| TEST_008_05 | `run()` com `interval_hours == 0` | Retorna sem chamar `_send_report` |

---

## 8. Tratamento de Erros

| Erro | Comportamento |
|---|---|
| `Exception` em `get_performance_metrics()` | Log `error_type=type(exc).__name__`; skip ciclo |
| `Exception` em `notifier.send()` | Log warning; skip ciclo (Notifier já garante no-raise) |
| `asyncio.CancelledError` em `run()` | Propaga (shutdown graceful do asyncio.gather) |

---

## 9. Riscos

| Risco | Mitigação |
|---|---|
| Token Telegram vazar em log | `TelegramNotifier` já usa `type(exc).__name__` — risco inexistente |
| Reporter bloquear shutdown | `CancelledError` propagado normalmente |
| Intervalo muito curto gerar spam | `ge=0` na validação; `0` desabilita; usuário controla |

---

## 10. Definition of Done

- [x] `PerformanceReporter` implementado em `src/notifications/performance_reporter.py`
- [x] `NotificationEvent.PERFORMANCE_REPORT` adicionado em `src/notifications/events.py`
- [x] `PerformanceReportEvent` com `to_message()` em `src/notifications/events.py`
- [x] `performance_report_interval_hours` adicionado em `src/config/settings.py`
- [x] `.env.example` atualizado com `PERFORMANCE_REPORT_INTERVAL_HOURS`
- [x] `PerformanceReporter` integrado em `src/main.py` no `asyncio.gather()`
- [x] 5 testes passando (`TEST_008_01` a `TEST_008_05`)
- [x] Suite completa passando sem regressões
- [x] `ruff check` e `ruff format` limpos

---

## 11. Plano de Entrega

### task_001 — Configuração e eventos (P1)

Adicionar campo `performance_report_interval_hours` em settings e `PERFORMANCE_REPORT_INTERVAL_HOURS`
no `.env.example`. Adicionar `NotificationEvent.PERFORMANCE_REPORT` e `PerformanceReportEvent`
em `events.py`.

### task_002 — Implementação do PerformanceReporter (P1)

Criar `src/notifications/performance_reporter.py` com `PerformanceReporter`. Criar testes
`tests/notifications/test_performance_reporter.py` (TEST_008_01 a TEST_008_05).

### task_003 — Integração no main.py (P1)

Adicionar `PerformanceReporter` como task paralela no `asyncio.gather()` de `_main()`.

### task_004 — QA gate (P2)

`pytest tests/ -v --tb=short` + `ruff check` + `ruff format` + atualizar todos os status files.
