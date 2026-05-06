# SPEC_009 — Análise de Performance por Símbolo e Timeframe

**ID:** SPEC_009
**Status:** Concluída
**Data:** 2026-05-05
**Autor:** Time A (Refinamento)
**Executores:** Time B (Execução)
**Skills requeridas:** Python, MongoDB, FastAPI, pytest
**Depende de:** SPEC_006, SPEC_007
**Conexão PRD:** §Fase 2 "Análise de performance por símbolo e timeframe". SPEC_006 Non-Goals:
"Filtros por data range ou símbolo no endpoint MVP (extensão futura)".

---

## 1. Título e Resumo

### 1.1 Nome da Funcionalidade

Análise de performance desagregada por símbolo e por timeframe

### 1.2 Resumo (High-Level Definition)

**O que é:** Dois novos endpoints REST (`GET /performance/by-symbol` e
`GET /performance/by-timeframe`) que retornam as 6 métricas RF-11 agrupadas por símbolo ou
timeframe, permitindo ao operador identificar quais ativos e quais janelas de tempo estão gerando
resultado positivo.

**Por que estamos fazendo:** `GET /performance` retorna apenas métricas globais — o operador não
sabe quais símbolos ou timeframes são lucrativos. Isso viola o Princípio 7 do Manifesto (Evolução
Orientada por Dados). O SPEC_006 declarou explicitamente este item como "extensão futura".

**Valor de negócio:** Permite ao operador desativar ou ajustar símbolos com desempenho ruim,
melhorando o retorno ajustado ao risco da carteira de forma guiada por dados.

**Conexão com PRD/SPEC:** PRD §Fase 2 "Análise de performance por símbolo e timeframe".
SPEC_006 §2.2 Non-Goals: "Filtros por data range ou símbolo no endpoint MVP (extensão futura)".

---

## 2. Objetivos e Escopo

### 2.1 Objetivos (o que será entregue)

- [x] Função auxiliar `_calc_metrics(trades)` extraída de `get_performance_metrics()` — sem mudança
  de comportamento existente
- [x] `MongoRepository.get_performance_by_symbol()` → métricas RF-11 por símbolo
- [x] `MongoRepository.get_performance_by_timeframe()` → métricas RF-11 por timeframe
- [x] `GET /performance/by-symbol` — retorna dict agrupado por símbolo + `generated_at`
- [x] `GET /performance/by-timeframe` — retorna dict agrupado por timeframe + `generated_at`
- [x] 7 testes cobrindo repositório e endpoints (TEST_009_01 a TEST_009_07)

### 2.2 Fora do Escopo (Non-Goals)

- **Não inclui:** Filtros por data range (ex.: últimos 30 dias)
- **Não inclui:** Visualização gráfica no frontend (Fase 2 mais avançada)
- **Não inclui:** Endpoint de combinação símbolo+timeframe (cruzamento)
- **Não inclui:** Alertas automáticos quando símbolo degrada
- **Não inclui:** Backtesting sobre dados históricos

---

## 3. Referências

| Documento | Seção | Relevância |
|---|---|---|
| `PRD.md` | §Fase 2 linha 223 | Requisito de origem |
| `docs/SDD/SPEC_006_.../SPEC.md` | §2.2 Non-Goals | "Filtros por símbolo — extensão futura" |
| `src/storage/repository.py` | `get_performance_metrics()` | Lógica a reusar via `_calc_metrics()` |
| `src/api/routes/performance.py` | `GET /performance` | Base para novos endpoints |
| `src/trading/order_manager.py` | `Trade.symbol`, `Trade.timeframe` | Campos disponíveis no MongoDB |

---

## 4. User Stories

| ID | Como... | Quero... | Para... |
|---|---|---|---|
| US-009-01 | Operador | Ver métricas de cada símbolo separadamente | Identificar quais ativos remover da watchlist |
| US-009-02 | Operador | Ver métricas de cada timeframe separadamente | Ajustar quais janelas temporais operar |
| US-009-03 | Operador | Que `GET /performance` continue funcionando igual | Não quebrar integrações existentes |

---

## 5. Design e Arquitetura

### 5.1 Refactor do repositório (não-breaking)

```python
def _calc_metrics(trades: list[dict]) -> dict:
    """Calcula as 6 métricas RF-11 sobre uma lista de trades fechados."""
    # lógica extraída de get_performance_metrics()
    ...

async def get_performance_metrics(self) -> dict[str, float | int]:
    trades = await self._fetch_closed_trades(project_group_fields=False)
    return _calc_metrics(trades)

async def get_performance_by_symbol(self) -> dict[str, dict]:
    trades = await self._fetch_closed_trades(project_group_fields=True)
    groups: dict[str, list] = {}
    for t in trades:
        groups.setdefault(t["symbol"], []).append(t)
    return {sym: _calc_metrics(ts) for sym, ts in groups.items()}

async def get_performance_by_timeframe(self) -> dict[str, dict]:
    trades = await self._fetch_closed_trades(project_group_fields=True)
    groups: dict[str, list] = {}
    for t in trades:
        groups.setdefault(t.get("timeframe", "unknown"), []).append(t)
    return {tf: _calc_metrics(ts) for tf, ts in groups.items()}
```

### 5.2 Novos endpoints

```
GET /performance/by-symbol    → {by_symbol: {BTCUSDT: {...}, ...}, generated_at: "..."}
GET /performance/by-timeframe → {by_timeframe: {4h: {...}, ...}, generated_at: "..."}
```

Ambos: 503 se `app.state.repository` for `None`.

---

## 6. Regras de Negócio e Invariantes

| ID | Invariante |
|---|---|
| INV-009-01 | `get_performance_metrics()` continua retornando resultado idêntico após refactor |
| INV-009-02 | Símbolo sem trades fechados não aparece no dict de retorno |
| INV-009-03 | Trade sem campo `timeframe` agrupa em chave `"unknown"` |
| INV-009-04 | Endpoints retornam 503 se repositório indisponível |

---

## 7. Testes

| ID | Cenário | Critério de Aceite |
|---|---|---|
| TEST_009_01 | `get_performance_by_symbol` com 2 símbolos | Retorna dict com 2 chaves, métricas independentes |
| TEST_009_02 | `get_performance_by_symbol` sem trades | Retorna `{}` vazio |
| TEST_009_03 | `get_performance_by_timeframe` com 2 timeframes | Retorna dict com 2 chaves |
| TEST_009_04 | `get_performance_metrics()` após refactor | Resultado idêntico ao esperado (não-breaking) |
| TEST_009_05 | `GET /performance/by-symbol` retorna 200 | Estrutura `{by_symbol: {...}, generated_at}` |
| TEST_009_06 | `GET /performance/by-timeframe` retorna 200 | Estrutura `{by_timeframe: {...}, generated_at}` |
| TEST_009_07 | Ambos endpoints sem repositório | Retornam 503 |

---

## 8. Tratamento de Erros

| Erro | Comportamento |
|---|---|
| `app.state.repository is None` | 503 `{"error": "database_unavailable"}` |
| `Exception` na query MongoDB | 503 `{"error": "database_unavailable"}` |

---

## 9. Definition of Done

- [x] `_calc_metrics()` extraído e `get_performance_metrics()` usando-a
- [x] `get_performance_by_symbol()` e `get_performance_by_timeframe()` implementados
- [x] `GET /performance/by-symbol` e `GET /performance/by-timeframe` funcionando
- [x] 7 testes passando (TEST_009_01 a TEST_009_07)
- [x] `GET /performance` sem regressão
- [x] Suite completa passando
- [x] `ruff check` e `ruff format` limpos

---

## 10. Plano de Entrega

### task_001 — Refactor e novos métodos no repositório (P1)

Extrair `_calc_metrics()`. Implementar `get_performance_by_symbol()` e
`get_performance_by_timeframe()`. Verificar que `get_performance_metrics()` é não-breaking.

### task_002 — Novos endpoints REST (P1)

Adicionar `GET /performance/by-symbol` e `GET /performance/by-timeframe` em
`src/api/routes/performance.py`.

### task_003 — Testes (P1)

Criar `tests/storage/test_repository_performance.py` (TEST_009_01 a 04) e
`tests/api/test_performance_by_group.py` (TEST_009_05 a 07).

### task_004 — QA gate (P2)

`pytest tests/ --tb=short -q` + `ruff check` + `ruff format` + atualizar status files.
