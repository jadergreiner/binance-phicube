# Especificação Técnica — Dashboard V2

## Objetivo

Definir implementação do novo dashboard com foco operacional:

- Quantos símbolos abertos.
- Símbolos mais lucrativos.
- Melhores e piores trades.
- Visão reordenável por símbolo, PnL e tamanho.

Compatível com endpoints já existentes no projeto.

## Endpoints (fonte de dados)

- `GET /positions`
- `WS /ws/positions`
- `GET /bot-activity`
- `GET /trades/history`
- `GET /trades/open`
- `GET /signals/history`
- `GET /performance`
- `GET /performance/by-symbol`
- `GET /performance/by-timeframe`

## Contratos de dados (camada de UI)

### 1) Snapshot principal — `/positions` e `/ws/positions`

Campos relevantes:

- `positions[]`:
  - `symbol: string`
  - `side: "LONG" | "SHORT"`
  - `quantity: number` (canônico)
  - `size: number` (deprecated; alias)
  - `leverage: number`
  - `entry_price: number`
  - `sl_price: number | null`
  - `tp_price: number | null`
  - `mark_price: number`
  - `unrealized_pnl_usdt: number` (canônico)
  - `unrealized_pnl: number` (deprecated; alias)
  - `margin_used_usdt: number`
  - `position_size_usdt: number | null`
  - `roi_adjusted_pct: number | null`
  - `updated_at: string`
  - `updated_at_br: string`
- `summary`:
  - `total_exposure_usdt: number`
  - `total_margin_used_usdt: number`
  - `total_unrealized_pnl_usdt: number`
  - `account_equity_usdt: number | null`
  - `exposure_to_equity_ratio: number | null`
  - `connection_status: "online" | "degraded" | "cached" | "offline"`
- `status: string`
- `analysis: object`
- `signal_telemetry: array`
- `deprecated_fields`:
  - `size -> quantity`
  - `unrealized_pnl -> unrealized_pnl_usdt`

Regra: frontend deve consumir apenas `quantity` e `unrealized_pnl_usdt`.

### 2) Trades

- `GET /trades/history`:
  - `trades[]` com `symbol`, `direction`, `entry_price`, `exit_price`, `stop_loss`, `take_profit`, `pnl_usdt`, `status`, `closed_at`.
- `GET /trades/open`:
  - `trades[]` com `symbol`, `opened_at`, `entry_price`, `current_price`, `margin_used_usdt`, `unrealized_pnl_usdt`.

### 3) Performance

- `GET /performance`: métricas globais.
- `GET /performance/by-symbol`: agregação por símbolo.
- `GET /performance/by-timeframe`: agregação por timeframe.

## Estrutura HTML (desktop)

```html
<main id="dashboard-v2">
  <header id="topbar">...</header>

  <section id="kpis">
    <article data-kpi="open_symbols"></article>
    <article data-kpi="open_pnl"></article>
    <article data-kpi="exposure"></article>
    <article data-kpi="win_rate"></article>
  </section>

  <section id="highlights">
    <div id="top-profitable-symbols"></div>
    <div id="top-losing-symbols"></div>
  </section>

  <section id="positions-controls">
    <input id="filter-symbol" />
    <select id="filter-side"></select>
    <select id="sort-key"></select>
    <button id="sort-dir"></button>
    <button id="save-view"></button>
  </section>

  <section id="positions-table">
    <table>
      <thead>
        <tr>
          <th data-sort="symbol">Símbolo</th>
          <th>Lado</th>
          <th data-sort="quantity">Tamanho</th>
          <th>Entry</th>
          <th>SL</th>
          <th>TP</th>
          <th>Mark</th>
          <th data-sort="unrealized_pnl_usdt">PnL</th>
          <th>ROI</th>
          <th>Atualizado</th>
        </tr>
      </thead>
      <tbody id="positions-body"></tbody>
    </table>
  </section>

  <section id="trades-panels">
    <div id="best-trades"></div>
    <div id="worst-trades"></div>
  </section>
</main>
```

## Estrutura HTML (mobile)

- Mesmo conteúdo em coluna única.
- `positions-controls` em drawer/modal.
- Tabela substituída por cards:
  - `symbol`, `side`, `quantity`, `entry/sl/tp`, `pnl`, `roi`.

## Estados de UI

- `loading`: skeleton de KPI, lista e tabela.
- `online`: dados em tempo real via websocket.
- `degraded/cached`: banner com aviso e timestamp de último snapshot.
- `offline`: estado de indisponibilidade com retry.
- `empty`: sem posições/trades para o filtro atual.
- `error`: falha de fetch com mensagem e ação de recarregar.

## Ordenação e preferências

### Critérios

- `symbol`
- `unrealized_pnl_usdt`
- `quantity`

### Regras

- Clique no cabeçalho alterna `asc -> desc -> asc`.
- Ordenação padrão inicial: `unrealized_pnl_usdt desc`.
- Filtros aplicados antes da ordenação.
- Persistir em `localStorage`:
  - `dashboard.sort_key`
  - `dashboard.sort_dir`
  - `dashboard.filter_symbol`
  - `dashboard.filter_side`

## Formatação de preços

Para `Entry`, `SL`, `TP`, `Mark`:

- `minimumFractionDigits: 2`
- `maximumFractionDigits: 8`

Objetivo: manter precisão para símbolos fracionários sem truncamento agressivo.

## Cálculos de destaque

- `open_symbols_count`: `positions.length`.
- `top_profitable_symbols`: top N por `unrealized_pnl_usdt desc`.
- `top_losing_symbols`: top N por `unrealized_pnl_usdt asc`.
- `best_trades`: top N de `trades.history` por `pnl_usdt desc`.
- `worst_trades`: top N de `trades.history` por `pnl_usdt asc`.

## Plano de implementação

1. Extrair estado de ordenação/filtros para módulo único.
2. Aplicar contrato canônico (`quantity`, `unrealized_pnl_usdt`) em toda renderização.
3. Introduzir seção de destaques com dados de `/positions`.
4. Introduzir melhores/piores trades com `/trades/history`.
5. Implementar persistência local das preferências.
6. Validar estados (`online`, `degraded`, `cached`, `offline`, `empty`).
7. Testes de regressão de renderização e ordenação.

## Critérios de aceite

- Usuário consegue ordenar por símbolo, PnL e tamanho sem recarregar.
- Cards KPI e destaques atualizam com websocket/fallback polling.
- Entry/SL/TP respeitam precisão dinâmica por símbolo.
- Campos canônicos usados internamente; aliases legados não são necessários para lógica.
- Dashboard continua funcional em `degraded` e `cached`.
