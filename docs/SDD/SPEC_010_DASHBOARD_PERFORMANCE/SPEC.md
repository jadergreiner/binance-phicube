# SPEC_010 — Dashboard de Performance em Tempo Real

**ID:** SPEC_010
**Status:** Concluída
**Data:** 2026-05-05
**Autor:** Time A (Refinamento)
**Executores:** Time B (Execução)
**Skill de validação:** `sdd-spec-driven-development`, `qa-review`

---

## 1. Título e Resumo

### 1.1 Nome da Funcionalidade

Dashboard de Performance em Tempo Real

### 1.2 Resumo (High-Level Definition)

**O que é:** Extensão do painel frontend existente para exibir as métricas RF-11 de performance
de trades (globais, por símbolo e por timeframe) com polling automático a cada 60 segundos.

**Por que estamos fazendo:** As métricas de performance existem no backend (SPEC_006 + SPEC_009),
mas não são visíveis no painel. O operador precisa chamar a API diretamente para consultar win rate,
PnL acumulado, drawdown e profit factor — o que viola o OKR de "Evolução Orientada por Dados".

**Valor de negócio:** O operador visualiza em tempo real se o bot está performando conforme o
esperado, por símbolo e por timeframe, sem intervenção manual.

**Conexão com PRD/SPEC:** PRD §Fase 2 "Dashboard de performance em tempo real". Dependências:
SPEC_006 (métricas globais), SPEC_009 (por símbolo e por timeframe).

---

## 2. Objetivos e Escopo

### 2.1 Objetivos (o que será entregue)

- [x] Seção HTML `.performance-panel` com 6 cards de métricas globais
- [x] Tabela por símbolo com as 6 métricas RF-11
- [x] Tabela por timeframe com as 6 métricas RF-11
- [x] Polling automático a cada 60 segundos via `fetchPerformance()`
- [x] Falha nos endpoints de performance não afeta o painel de posições (INV-010-01)
- [x] Estilos CSS consistentes com o tema dark existente
- [x] Testes unitários para o endpoint `GET /performance`

### 2.2 Fora do Escopo (Non-Goals)

- **Não inclui:** Gráficos ou visualizações históricas — será SPEC_011+
- **Não inclui:** Filtros de data range — deferred
- **Não inclui:** WebSocket streaming de performance — REST polling é suficiente para dados históricos
- **Não inclui:** Mudanças no backend — todos os endpoints já estão implementados

---

## 3. Referências

| Documento | Seção | Relevância |
|---|---|---|
| `PRD.md` | §Fase 2 | "Dashboard de performance em tempo real" |
| `SPEC_006/SPEC.md` | — | Métricas RF-11 globais (pré-requisito) |
| `SPEC_009/SPEC.md` | — | Métricas por símbolo e timeframe (pré-requisito) |
| `src/api/routes/performance.py` | — | 3 endpoints prontos |

---

## 4. Histórias de Usuário e Requisitos

### US-010-01: Visualizar métricas globais de performance

> Como **operador**, quero **ver win rate, PnL, drawdown e profit factor no painel** para
> **avaliar se o bot está performando conforme o método Phicube**.

**Critérios de Aceitação:**

```text
DADO   que o bot tem trades fechados no MongoDB
QUANDO o painel carrega
ENTÃO  a seção "Performance de Trades" exibe 6 cards com as métricas atualizadas
```

- [x] AC-01: Cards exibem total_trades, win_rate_pct, total_pnl_usdt, avg_rrr, max_drawdown_usdt, profit_factor
- [x] AC-02: Polling atualiza a cada 60 segundos automaticamente
- [x] AC-03: Sem trades fechados → cards mostram "—" ou "0", sem erros JS

### US-010-02: Visualizar performance por símbolo e timeframe

> Como **operador**, quero **ver quais símbolos e timeframes estão lucrando** para
> **identificar onde o método funciona melhor**.

**Critérios de Aceitação:**

```text
DADO   que há trades fechados de múltiplos símbolos/timeframes
QUANDO o painel exibe a seção de performance
ENTÃO  duas tabelas mostram métricas individuais por símbolo e por timeframe
```

- [x] AC-01: Tabela "Por Símbolo" com uma linha por símbolo ativo
- [x] AC-02: Tabela "Por Timeframe" com uma linha por timeframe ativo
- [x] AC-03: PnL positivo exibido em verde; negativo em vermelho

---

## 5. Design e Arquitetura

### 5.1 Estrutura do Frontend

**Hierarquia HTML adicionada em `index.html`:**

```
<section class="performance-panel">
  <div class="panel-header">
    <h2>Performance de Trades</h2>
    <span id="performance-status">—</span>
  </div>
  <div class="performance-cards">          ← 6 cards globais
    <article class="performance-card" />   × 6
  </div>
  <div class="performance-group">          ← Tabela por símbolo
    <table class="performance-table" />
  </div>
  <div class="performance-group">          ← Tabela por timeframe
    <table class="performance-table" />
  </div>
</section>
```

### 5.2 Contratos de API consumidos

| Endpoint | Resposta chave |
|----------|---------------|
| `GET /performance` | `{total_trades, win_rate_pct, total_pnl_usdt, avg_rrr, max_drawdown_usdt, profit_factor, generated_at}` |
| `GET /performance/by-symbol` | `{by_symbol: {SYMBOL: {métricas}}, generated_at}` |
| `GET /performance/by-timeframe` | `{by_timeframe: {TF: {métricas}}, generated_at}` |

### 5.3 Fluxo de Dados

```
bootstrap()
  └─ fetchPerformance()  [chamada inicial + setInterval 60s]
       └─ Promise.all([/performance, /by-symbol, /by-timeframe])
            └─ renderPerformance(global, bySymbol, byTimeframe)
                 ├─ popula 6 cards globais
                 ├─ renderGroupTable(perfBySymbolBody, bySymbol)
                 └─ renderGroupTable(perfByTimeframeBody, byTimeframe)
```

---

## 6. Regras de Negócio e Restrições

### 6.1 Invariantes de Negócio

| ID | Invariante | Violação → Ação |
|---|---|---|
| INV-010-01 | Falha em `fetchPerformance()` não afeta painel de posições | try/catch silencioso em `fetchPerformance()` |
| INV-010-02 | Sem trades fechados → UI mostra "—" ou "0", nunca erro JS | Verificar `data || {}` antes de iterar |
| INV-010-03 | Polling de performance usa `setInterval` independente do WebSocket | Dois temporizadores separados em `bootstrap()` |
| INV-010-04 | `GET /performance` continua retornando as 6 métricas globais sem regressão | Coberto por TEST_010_01 |

---

## 7. Testes e Validação

### 7.1 Testes Unitários

| ID | Descrição | Cenário | Prioridade |
|---|---|---|---|
| TEST_010_01 | GET /performance retorna 200 com 6 métricas | Repositório com dados → 200 + estrutura completa | Alta |
| TEST_010_02 | GET /performance retorna 503 sem repositório | `app.state.repository = None` → 503 | Alta |

### 7.2 Cobertura existente (SPEC_009)

- TEST_009_05: `GET /performance/by-symbol` → 200
- TEST_009_06: `GET /performance/by-timeframe` → 200
- TEST_009_07: ambos → 503 sem repositório

### 7.3 Evidências Requeridas na PR

- [x] `pytest tests/ --tb=short -q` com todas as asserções passando
- [x] `ruff check src/ tests/` limpo
- [x] Frontend exibe seção "Performance de Trades" sem erros JS

---

## 8. Tratamento de Erros

| Erro / Condição | Causa | Ação do Sistema |
|---|---|---|
| Qualquer endpoint retorna 503 | MongoDB indisponível | `fetchPerformance()` retorna silenciosamente; UI permanece com "—" |
| Exceção de rede em `fetch()` | API offline | catch silencioso — painel de posições não é afetado |
| `by_symbol` ou `by_timeframe` vazio `{}` | Sem trades fechados | `renderGroupTable()` exibe "Sem trades fechados." |

---

## 9. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Variáveis CSS inexistentes | Baixo — estilos quebrados | Verificar `style.css` antes de adicionar novas classes |
| Polling aumentar carga no servidor | Baixo — apenas 3 req/60s | Intervalo de 60s é adequado para dados históricos |

---

## 10. Definição de Pronto (DoD Global)

- [x] SPEC aprovada pelo Time A
- [x] US-010-01 e US-010-02 com critérios de aceitação verificados
- [x] Implementação aderente a todos os contratos da seção 5
- [x] Nenhuma invariante da seção 6.1 violada em nenhum cenário de teste
- [x] `pytest` com 100% das asserções críticas passando
- [x] Rastreabilidade PRD → SPEC_010 → Teste → Código comprovada

---

## 11. Plano de Entrega

1. Criar documentação SPEC_010
2. Implementar seção HTML em `index.html`
3. Implementar `fetchPerformance()`, `renderPerformance()`, `renderGroupTable()` em `app.js`
4. Adicionar estilos `.performance-*` em `style.css`
5. Criar `tests/api/test_performance_endpoints.py`
6. QA Gate: pytest + ruff

---

## Histórico

- **2026-05-05:** Criação e implementação completa da SPEC_010.
