# SPEC_035 — Tasks de Implementação

**Versão:** 2.0  
**Data:** 2026-05-13  
**Status:** Pronto para execução  
**Tempo estimado:** 8 dev-days  
**Responsável:** Dev Frontend (1 pessoa)  

---

## 📋 Índice

- [Sprint 1: Setup Inicial (1.5 dev-days)](#sprint-1-setup-inicial-15-dev-days)
- [Sprint 2: Componentes & State (3.5 dev-days)](#sprint-2-componentes--state-35-dev-days)
- [Sprint 3: API, Testes & DevOps (2.5 dev-days)](#sprint-3-api-testes--devops-25-dev-days)
- [Sprint 4: Documentação & Validação (0.5 dev-days)](#sprint-4-documentação--validação-05-dev-days)

---

## Sprint 1: Setup Inicial (1.5 dev-days)

### TASK_035_S1_01: Decisão Framework & Instalação Vite+Vue 3

**Tipo:** Setup/Spike  
**Estimativa:** 3h  
**Dependências:** Nenhuma  
**Prioridade:** P0 (bloqueadora)

**Descrição:**
- Confirmar Vue.js 3 como framework (decidido em SPEC_035 §2)
- Criar pasta `frontend/` na raiz do projeto
- Executar: `npm create vite@latest frontend -- --template vue-ts`
- Navegar para `frontend/` e executar `npm install`
- Validar que `npm run dev` roda em `localhost:3000`
- Validar que `npm run build` produz `dist/` sem erros
- Validar que `npm run test` executa (sem testes ainda)

**Artefatos:**
- `frontend/package.json` (com vue@3.5+, vite@6+)
- `frontend/vite.config.ts` (existente, padrão Vite)
- `frontend/tsconfig.json` (existente, padrão TS)

**Critério de Aceite:**
- ✅ `npm run dev` roda sem erros em port 3000
- ✅ `npm run build` completa, `dist/` criado
- ✅ `npm run test` executa (Vitest configurado)
- ✅ Não há warnings críticos no build
- ✅ TypeScript não rejeita arquivos padrão Vue

**Validador:** @coder  
**Revisado por:** @qa-review

---

### TASK_035_S1_02: Dependências & Configurações Iniciais

**Tipo:** Setup  
**Estimativa:** 2h  
**Dependências:** TASK_035_S1_01  
**Prioridade:** P0 (bloqueadora)

**Descrição:**
- Instalar dependências core: `npm install vue-router@4 pinia@2 axios@1.7`
- Instalar dev deps: `npm install --save-dev typescript@5.6 @vitejs/plugin-vue@5 @vue/test-utils@2 vitest@2 jsdom@24 eslint@9 prettier@3 @vitest/ui`
- Opcional: `npm install chart.js vue-chartjs` (para PriceChart futura)
- Criar `.prettierrc`:
  ```json
  {
    "semi": true,
    "trailingComma": "es5",
    "singleQuote": true,
    "printWidth": 100,
    "tabWidth": 2
  }
  ```
- Criar `.eslintrc.json` (configuração Vue + TypeScript)
- Criar `frontend/.env.local`:
  ```
  VITE_API_BASE_URL=http://localhost:8080/api/v1
  VITE_APP_ENV=development
  ```
- Adicionar scripts em `package.json`:
  ```json
  {
    "scripts": {
      "dev": "vite",
      "build": "vue-tsc --noEmit && vite build",
      "preview": "vite preview",
      "test": "vitest",
      "test:coverage": "vitest --coverage",
      "type-check": "vue-tsc --noEmit",
      "lint": "eslint src --ext .ts,.vue",
      "format": "prettier --write src/"
    }
  }
  ```

**Artefatos:**
- `frontend/.prettierrc`
- `frontend/.eslintrc.json`
- `frontend/.env.local`
- `frontend/package.json` (atualizado)

**Critério de Aceite:**
- ✅ `npm install` completa sem erros
- ✅ `npm run lint` executa (pode ter warnings, nenhum erro crítico)
- ✅ `npm run type-check` executa
- ✅ `npm run format` formata código sem erros
- ✅ Variáveis de ambiente carregam corretamente

**Validador:** @coder  
**Revisado por:** @lint-on-edit, @qa-review

---

### TASK_035_S1_03: Estrutura de Pastas & Configuração TypeScript Strict

**Tipo:** Setup  
**Estimativa:** 1h  
**Dependências:** TASK_035_S1_01  
**Prioridade:** P0 (bloqueadora)

**Descrição:**
- Criar estrutura de pastas em `frontend/src/`:
  ```
  frontend/src/
  ├── components/          # Componentes reutilizáveis
  ├── views/               # Páginas/Views
  ├── stores/              # Pinia stores
  ├── services/            # API service, types, config
  ├── router/              # Vue Router config
  ├── styles/              # CSS global
  ├── App.vue
  ├── main.ts
  └── vite-env.d.ts
  ```
- Criar `frontend/public/` com `favicon.ico`, `robots.txt`
- Configurar `tsconfig.json` com flags strict (§7.3 da SPEC_035):
  - `"strict": true`
  - `"noImplicitAny": true`
  - `"strictNullChecks": true`
  - `"noUnusedLocals": true`
  - `"noUnusedParameters": true`
  - `"noImplicitReturns": true`
- Criar `frontend/tests/` para testes unitários
- Criar `frontend/vitest.config.ts` com config base

**Artefatos:**
- Pasta structure criada
- `frontend/tsconfig.json` (strict mode)
- `frontend/vitest.config.ts` (configuração base)

**Critério de Aceite:**
- ✅ Estrutura de pasta criada e vazia
- ✅ `npm run type-check` executa sem erros (arquivo vazio aceitável)
- ✅ Vitest consegue descobrir arquivos `.spec.ts`

**Validador:** @coder  
**Revisado por:** @qa-review

---

## Sprint 2: Componentes & State (3.5 dev-days)

### TASK_035_S2_01: Vue Router Setup & Views Skeleton

**Tipo:** Feature  
**Estimativa:** 1.5h  
**Dependências:** TASK_035_S1_03  
**Prioridade:** P0 (bloqueadora)

**Descrição:**
- Criar `frontend/src/router/index.ts` com:
  - Importar `createRouter`, `createWebHistory` de `vue-router`
  - Definir 5 rotas:
    - `/` → DashboardView (lazy-loaded)
    - `/positions` → PositionsView (lazy-loaded)
    - `/history` → HistoryView (lazy-loaded)
    - `/settings` → SettingsView (lazy-loaded)
    - `/:pathMatch(.*)` → NotFoundView (catch-all para 404)
  - Configurar lazy-loading com `defineAsyncComponent`
  - Adicionar navigation guard básico (placeholder para SPEC_036)
- Criar `frontend/src/views/DashboardView.vue` (empty template)
- Criar `frontend/src/views/PositionsView.vue` (empty template)
- Criar `frontend/src/views/HistoryView.vue` (empty template)
- Criar `frontend/src/views/SettingsView.vue` (empty template)
- Criar `frontend/src/views/NotFoundView.vue` com botão "Voltar ao Dashboard"
- Atualizar `frontend/src/App.vue` para usar `<router-view>`
- Atualizar `frontend/src/main.ts` para usar router

**Artefatos:**
- `frontend/src/router/index.ts`
- `frontend/src/views/*.vue` (5 arquivos)
- `frontend/src/App.vue` (atualizado)
- `frontend/src/main.ts` (atualizado)

**Critério de Aceite:**
- ✅ `npm run dev` roda, navegação no browser funciona
- ✅ Clique em links muda view sem reload (SPA puro)
- ✅ Rota desconhecida redireciona para 404
- ✅ Browser back/forward funciona
- ✅ TypeScript strict sem erros

**Validador:** @coder  
**Revisado por:** @qa-review

---

### TASK_035_S2_02: Layout Components (Navbar & Footer)

**Tipo:** Feature  
**Estimativa:** 1h  
**Dependências:** TASK_035_S2_01  
**Prioridade:** P1

**Descrição:**
- Criar `frontend/src/components/Layout/Navbar.vue` com:
  - Logo/título "Phicube Dashboard"
  - Links de navegação: Dashboard, Posições, Histórico, Configuração
  - Usar `<router-link>` para navegação SPA
  - Estilos básicos (navbar escuro, links claros)
- Criar `frontend/src/components/Layout/Footer.vue` com:
  - Versão do bot (será preenchido dinamicamente)
  - Status (healthy/degraded/unhealthy)
  - Copyright/footer text
  - Estilos básicos (footer escuro, text pequeno)
- Atualizar `frontend/src/App.vue` para incluir Navbar + router-view + Footer
- Criar `frontend/src/styles/main.css` com variáveis CSS:
  ```css
  :root {
    --color-primary: #2c3e50;
    --color-secondary: #3498db;
    --color-success: #27ae60;
    --color-danger: #e74c3c;
    --color-warning: #f39c12;
    --color-text: #2c3e50;
    --color-bg: #ecf0f1;
    --color-border: #bdc3c7;
  }
  ```

**Artefatos:**
- `frontend/src/components/Layout/Navbar.vue`
- `frontend/src/components/Layout/Footer.vue`
- `frontend/src/styles/main.css`
- `frontend/src/App.vue` (atualizado)

**Critério de Aceite:**
- ✅ Navbar exibido no topo de todas as views
- ✅ Links de navegação funcionam
- ✅ Footer exibido no rodapé
- ✅ Layout responsivo (básico)
- ✅ Sem console errors

**Validador:** @coder  
**Revisado por:** @qa-review

---

### TASK_035_S2_03: Componentes de UI (PositionTable, MetricCard, SignalBadge)

**Tipo:** Feature  
**Estimativa:** 1.5h  
**Dependências:** TASK_035_S2_02  
**Prioridade:** P1

**Descrição:**

#### PositionTable.vue
- Props: `positions: Position[]`, `loading: boolean`
- Exibir tabela com colunas: Symbol, Direction, Entry Price, Current Price, Quantity, PnL (USDT), PnL (%), SL, TP
- Funcionalidades:
  - Ordenação por clique no header
  - Filtro por Symbol (search box)
  - Cor verde para PnL positivo, vermelho para negativo
  - Loading spinner quando `loading=true`
  - Mensagem "Nenhuma posição aberta" quando vazio
- Emits: `sort` (coluna, direção)

#### MetricCard.vue
- Props: `label: string`, `value: number | string`, `delta?: number`, `unit?: string`
- Exibir card com:
  - Label (ex: "Total PnL")
  - Valor em grande
  - Delta e seta (se delta fornecido)
  - Cor: verde se delta > 0, vermelho se < 0
- Exemplo: "Total PnL: +500 USDT (↑ 2.5%)"

#### SignalBadge.vue
- Props: `direction: 'LONG' | 'SHORT' | 'NEUTRO'`
- Exibir badge com:
  - Texto ("LONG" / "SHORT" / "NEUTRO")
  - Cor: azul LONG, vermelho SHORT, cinza NEUTRO
  - Fonte monospace
  - Padding pequeno

**Artefatos:**
- `frontend/src/components/PositionTable.vue`
- `frontend/src/components/MetricCard.vue`
- `frontend/src/components/SignalBadge.vue`
- `frontend/src/styles/components.css` (estilos dos componentes)

**Critério de Aceite:**
- ✅ 3 componentes renderizam sem erros
- ✅ Props tipadas corretamente (TypeScript strict)
- ✅ PositionTable ordena ao clicar header
- ✅ PositionTable filtra por Symbol
- ✅ MetricCard exibe delta com seta
- ✅ SignalBadge exibe cores corretas
- ✅ Sem console errors

**Validador:** @coder  
**Revisado por:** @qa-review

---

### TASK_035_S2_04: Componentes Auxiliares (PriceChart, LoadingSpinner, ErrorBanner)

**Tipo:** Feature  
**Estimativa:** 1h  
**Dependências:** TASK_035_S2_03  
**Prioridade:** P2

**Descrição:**

#### LoadingSpinner.vue
- Props: `size?: 'small' | 'medium' | 'large'` (default: 'medium')
- Renderizar spinner animado (CSS-only, sem imagem)
- Animação: rotação contínua, duração 1s
- Cores: usar variável CSS `--color-secondary`

#### ErrorBanner.vue
- Props: `message: string`, `type?: 'error' | 'warning' | 'info'` (default: 'error')
- Exibir banner com:
  - Ícone (emoji ou símbolo simples)
  - Mensagem
  - Botão "Fechar" (emit `close`)
  - Cores: vermelho erro, amarelo warning, azul info
- Auto-desaparecer após 5s (emit `close`)

#### PriceChart.vue (mockado)
- Props: `prices?: number[]`, `labels?: string[]`, `loading: boolean`
- Por enquanto: exibir texto "Gráfico de preço em desenvolvimento"
- Placeholder para integração com Chart.js em SPEC_039
- Preparar estrutura para receber `canvas` ou `div` para Chart.js futura

**Artefatos:**
- `frontend/src/components/LoadingSpinner.vue`
- `frontend/src/components/ErrorBanner.vue`
- `frontend/src/components/PriceChart.vue`

**Critério de Aceite:**
- ✅ LoadingSpinner renderiza e anima
- ✅ ErrorBanner exibe mensagem e fecha
- ✅ PriceChart mockado (placeholder visível)
- ✅ Sem console errors
- ✅ TypeScript strict sem erros

**Validador:** @coder  
**Revisado por:** @qa-review

---

### TASK_035_S2_05: Pinia Store — Posições

**Tipo:** Feature  
**Estimativa:** 1h  
**Dependências:** TASK_035_S1_03  
**Prioridade:** P1

**Descrição:**
- Criar `frontend/src/stores/positionStore.ts` com:
  - State: `positions: Position[]`, `loading: boolean`, `error: string | null`, `lastUpdate: Date | null`
  - Computed:
    - `totalPnl`: soma de `pnl_usdt`
    - `winCount`: posições com PnL > 0
    - `lossCount`: posições com PnL < 0
  - Actions:
    - `fetchPositions()`: chamada a `getPositions()` (api.ts)
    - `updatePosition(updated: Position)`: atualiza posição no state
    - `clearPositions()`: limpa lista
- Usar Composition API (`defineStore` com function syntax)
- Importar types de `src/services/types.ts`

**Artefatos:**
- `frontend/src/stores/positionStore.ts`

**Critério de Aceite:**
- ✅ Store criada, tipada (TypeScript strict)
- ✅ Ações funcionam (fetchPositions, updatePosition, clearPositions)
- ✅ Computados calculam corretamente (totalPnl, winCount, lossCount)
- ✅ Loading state gerenciado
- ✅ Error handling implementado

**Validador:** @coder  
**Revisado por:** @qa-review

---

### TASK_035_S2_06: Pinia Store — Performance & UI

**Tipo:** Feature  
**Estimativa:** 1h  
**Dependências:** TASK_035_S2_05  
**Prioridade:** P1

**Descrição:**
- Criar `frontend/src/stores/performanceStore.ts` com:
  - State: `data: PerformanceResponse | null`, `loading: boolean`, `error: string | null`, `lastUpdate: Date | null`
  - Computed: `globalMetrics`: retorna `data.value?.global ?? null`
  - Actions: `fetchPerformance()`: chamada a `getPerformance()` (api.ts)
- Criar `frontend/src/stores/uiStore.ts` com:
  - State: `theme: 'light' | 'dark'` (default: 'light'), `sidebarOpen: boolean` (default: true), `notifications: Notification[]`
  - Actions:
    - `toggleTheme()`
    - `toggleSidebar()`
    - `addNotification(msg: string, type: 'info' | 'warning' | 'error')`
    - `removeNotification(id: string)`

**Artefatos:**
- `frontend/src/stores/performanceStore.ts`
- `frontend/src/stores/uiStore.ts`

**Critério de Aceite:**
- ✅ 2 stores criadas, tipadas
- ✅ performanceStore consome getPerformance()
- ✅ uiStore gerencia notificações
- ✅ Sem console errors

**Validador:** @coder  
**Revisado por:** @qa-review

---

## Sprint 3: API, Testes & DevOps (2.5 dev-days)

### TASK_035_S3_01: Tipos TypeScript & API Service

**Tipo:** Feature  
**Estimativa:** 1.5h  
**Dependências:** TASK_035_S1_03  
**Prioridade:** P0 (bloqueadora)

**Descrição:**
- Criar `frontend/src/services/types.ts` com tipos (do §4.2 da SPEC_035):
  - `Position` (symbol, direction, entry_price, current_price, quantity, pnl_usdt, pnl_pct, sl_price, tp_price, open_time, leverage, margin_usdt)
  - `PerformanceGlobal` (total_trades, win_rate_pct, total_pnl_usdt, avg_rrr, max_drawdown_usdt, profit_factor)
  - `PerformanceBySymbol` (symbol, idem acima)
  - `PerformanceByTimeframe` (timeframe, idem acima)
  - `PerformanceResponse` (global, by_symbol[], by_timeframe[])
  - `ApiError` (status, message, timestamp)
  - `HealthStatus` (status, uptime_seconds, mongodb_connected, binance_client_ok, timestamp)
- Criar `frontend/src/services/config.ts` com:
  - `API_BASE_URL` (lê VITE_API_BASE_URL ou `/api/v1`)
  - `REQUEST_TIMEOUT` (10000ms)
  - `MAX_RETRIES` (3)
- Criar `frontend/src/services/api.ts` com (§4.3 da SPEC_035):
  - axios client com baseURL, timeout, headers
  - Interceptor de resposta com retry (backoff exponencial 1s, 2s, 4s)
  - Função `getPositions()`: GET `/positions` → Position[]
  - Função `getPerformance()`: GET `/performance` → PerformanceResponse
  - Função `getHealth()`: GET `/health` → HealthStatus
  - Função `parseApiError()`: trata erro genérico → ApiError
  - Evento customizado 'auth:unauthorized' em erro 401

**Artefatos:**
- `frontend/src/services/types.ts`
- `frontend/src/services/config.ts`
- `frontend/src/services/api.ts`

**Critério de Aceite:**
- ✅ Tipos compilam sem erros (TypeScript strict)
- ✅ API service tipado corretamente
- ✅ Retry logic implementada
- ✅ Erro 401 dispara evento customizado
- ✅ Funções exportadas e testáveis

**Validador:** @coder  
**Revisado por:** @qa-review, @security-audit

---

### TASK_035_S3_02: Views Preenchidas — DashboardView & PositionsView

**Tipo:** Feature  
**Estimativa:** 1.5h  
**Dependências:** TASK_035_S2_06, TASK_035_S3_01  
**Prioridade:** P1

**Descrição:**

#### DashboardView.vue
- Usar `usePositionStore()` e `usePerformanceStore()`
- onMounted:
  - Chamar `fetchPositions()` e `fetchPerformance()`
  - Configurar polling a cada 60s (setInterval)
- Template:
  - Título "Dashboard"
  - 6 MetricCards em grid (Total Trades, Win Rate, Total PnL, Avg RRR, Max Drawdown, Profit Factor)
  - Tabela de performance por símbolo (by_symbol[])
  - Tabela de performance por timeframe (by_timeframe[])
  - LoadingSpinner enquanto `loading=true`
  - ErrorBanner se houver erro

#### PositionsView.vue
- Usar `usePositionStore()`
- onMounted: chamar `fetchPositions()` + polling 60s
- Template:
  - Título "Posições Abertas"
  - PositionTable com posições
  - Emitir `sort` evento (ordernar)
  - LoadingSpinner enquanto loading
  - ErrorBanner se houver erro

**Artefatos:**
- `frontend/src/views/DashboardView.vue` (preenchida)
- `frontend/src/views/PositionsView.vue` (preenchida)

**Critério de Aceite:**
- ✅ DashboardView exibe 6 metric cards
- ✅ PositionsView exibe tabela de posições
- ✅ Polling funciona a cada 60s
- ✅ Loading spinner aparece durante fetch
- ✅ Erro exibido em banner
- ✅ Navegação entre views não perde state

**Validador:** @coder  
**Revisado por:** @qa-review

---

### TASK_035_S3_03: Views Simples — HistoryView, SettingsView, NotFoundView

**Tipo:** Feature  
**Estimativa:** 1h  
**Dependências:** TASK_035_S2_02  
**Prioridade:** P2

**Descrição:**

#### HistoryView.vue
- Mockado nesta versão
- Template:
  - Título "Histórico de Trades"
  - Tabela vazia com msg "Histórico indisponível nesta versão"
  - Footer: "Será implementado em SPEC_035 v2.1"

#### SettingsView.vue
- Template:
  - Título "Configuração"
  - Cards com:
    - Versão do Bot (será preenchido via API futura)
    - Ambiente (VITE_APP_ENV)
    - API Base URL
    - MongoDB status (será preenchido via health check)
    - Binance status (será preenchido via health check)
  - Botão "Recarregar Status" que chama `getHealth()`

#### NotFoundView.vue
- Já criada em TASK_035_S2_01, melhorar:
  - Ícone/emoji 404
  - Mensagem "Página não encontrada"
  - Botão "Voltar ao Dashboard" que faz `router.push('/')`
  - Estilos centrados, legível

**Artefatos:**
- `frontend/src/views/HistoryView.vue`
- `frontend/src/views/SettingsView.vue`
- `frontend/src/views/NotFoundView.vue` (melhorada)

**Critério de Aceite:**
- ✅ 3 views renderizam sem erros
- ✅ HistoryView exibe mockado
- ✅ SettingsView exibe status
- ✅ NotFoundView funciona como fallback (/:pathMatch(.*))
- ✅ Botões funcionam

**Validador:** @coder  
**Revisado by:** @qa-review

---

### TASK_035_S3_04: Configuração Vite & Proxy Dev

**Tipo:** Setup  
**Estimativa:** 30m  
**Dependências:** TASK_035_S1_02  
**Prioridade:** P1

**Descrição:**
- Atualizar `frontend/vite.config.ts` (§7.2 da SPEC_035):
  - Resolver alias `@` → `src/`
  - Server proxy `/api` → `http://localhost:8080`
  - Server proxy `/health` → `http://localhost:8080`
  - Build config:
    - `target: 'esnext'`
    - `minify: 'terser'`
    - `sourcemap: false` (ou true em dev)
    - `rollupOptions.output.manualChunks`: separar vue-core, state, http
- Validar que `npm run dev` proxeia `/api` corretamente

**Artefatos:**
- `frontend/vite.config.ts` (atualizado)

**Critério de Aceite:**
- ✅ `npm run dev` roda e proxeia `/api` para localhost:8080
- ✅ Requests para `/api/v1/positions` chegam ao backend
- ✅ `npm run build` gera chunks otimizados

**Validador:** @coder  
**Revisado by:** @qa-review

---

### TASK_035_S3_05: Vitest Setup & Testes Unitários (Componentes)

**Tipo:** Feature  
**Estimativa:** 1.5h  
**Dependências:** TASK_035_S1_03, TASK_035_S2_03  
**Prioridade:** P1

**Descrição:**
- Atualizar `frontend/vitest.config.ts` (§8.1 da SPEC_035):
  - `globals: true`
  - `environment: 'jsdom'`
  - `setupFiles: ['./tests/setup.ts']`
  - Coverage config: 70% linhas/funções/branches/statements
- Criar `frontend/tests/setup.ts` com setup global (Vi mock, etc)
- Criar testes para componentes (§8.2 da SPEC_035):
  - `frontend/src/components/__tests__/PositionTable.spec.ts`:
    - Teste: renderiza posições
    - Teste: exibe spinner quando loading
    - Teste: ordena ao clicar header
    - Teste: filtra por symbol
  - `frontend/src/components/__tests__/MetricCard.spec.ts`:
    - Teste: renderiza label e valor
    - Teste: exibe delta com seta
    - Teste: cores corretas (verde/vermelho)
  - `frontend/src/components/__tests__/SignalBadge.spec.ts`:
    - Teste: renderiza direção LONG/SHORT/NEUTRO
    - Teste: cores corretas

**Artefatos:**
- `frontend/vitest.config.ts` (atualizado)
- `frontend/tests/setup.ts`
- `frontend/src/components/__tests__/PositionTable.spec.ts`
- `frontend/src/components/__tests__/MetricCard.spec.ts`
- `frontend/src/components/__tests__/SignalBadge.spec.ts`

**Critério de Aceite:**
- ✅ `npm run test` executa todos os testes
- ✅ Todos os testes passam (✓)
- ✅ Coverage ≥ 70% (PositionTable, MetricCard, SignalBadge)
- ✅ Sem console errors

**Validador:** @coder  
**Revisado by:** @qa-review

---

### TASK_035_S3_06: Testes Unitários (Store & API)

**Tipo:** Feature  
**Estimativa:** 1h  
**Dependências:** TASK_035_S2_05, TASK_035_S3_01  
**Prioridade:** P1

**Descrição:**
- Criar `frontend/src/stores/__tests__/positionStore.spec.ts` (§8.3):
  - Teste: fetchPositions atualiza state
  - Teste: totalPnl é computado corretamente
  - Teste: winCount conta posições positivas
  - Teste: updatePosition modifica posição
- Criar `frontend/src/stores/__tests__/performanceStore.spec.ts`:
  - Teste: fetchPerformance atualiza state
  - Teste: globalMetrics é computado
- Criar `frontend/src/services/__tests__/api.spec.ts` (§8.4):
  - Teste: getPositions faz chamada correta
  - Teste: getPerformance faz chamada correta
  - Teste: parseApiError extrai info
  - Teste: retry com backoff (conceitual)

**Artefatos:**
- `frontend/src/stores/__tests__/positionStore.spec.ts`
- `frontend/src/stores/__tests__/performanceStore.spec.ts`
- `frontend/src/services/__tests__/api.spec.ts`

**Critério de Aceite:**
- ✅ `npm run test` executa todos os testes de store e api
- ✅ Todos passam (✓)
- ✅ Coverage ≥ 70% cumulativo
- ✅ Mocks funcionam (vi.mock)

**Validador:** @coder  
**Revisado by:** @qa-review

---

### TASK_035_S3_07: Testes de Roteamento & TypeScript Strict

**Tipo:** Feature  
**Estimativa:** 1h  
**Dependências:** TASK_035_S2_01, TASK_035_S3_05  
**Prioridade:** P1

**Descrição:**
- Criar `frontend/src/router/__tests__/router.spec.ts` (§8.5):
  - Teste: rota `/` existe
  - Teste: rota `/positions` existe
  - Teste: rota `/404` existe
  - Teste: rota desconhecida redireciona para 404
  - Teste: guard verifica autenticação (placeholder)
- Adicionar script `npm run type-check` que executa `vue-tsc --noEmit`
- Validar que `npm run build` falha se houver erro TS (adicionar pre-build check)

**Artefatos:**
- `frontend/src/router/__tests__/router.spec.ts`
- `frontend/package.json` (script type-check)

**Critério de Aceite:**
- ✅ `npm run type-check` executa sem erros
- ✅ `npm run test` inclui testes de roteamento
- ✅ Todos os testes passam
- ✅ `npm run build` retorna erro se houver tipo inválido

**Validador:** @coder  
**Revisado by:** @qa-review

---

### TASK_035_S3_08: Dockerfile Multi-Stage & nginx.conf

**Tipo:** DevOps  
**Estimativa:** 1h  
**Dependências:** TASK_035_S3_04  
**Prioridade:** P1

**Descrição:**
- Criar `frontend/Dockerfile` (§7.4 da SPEC_035):
  - Stage 1: Node 20-alpine builder
    - COPY package*.json
    - npm ci
    - COPY source
    - npm run build
  - Stage 2: nginx:1.27-alpine
    - Remover default.conf
    - COPY nginx.conf customizado
    - COPY dist do builder
    - HEALTHCHECK: wget http://localhost/health
    - EXPOSE 80
    - CMD nginx -g "daemon off;"
- Criar `frontend/.dockerignore`:
  ```
  node_modules
  dist
  .git
  .gitignore
  README.md
  npm-debug.log
  .env*
  .vscode
  ```
- Criar `frontend/nginx.conf` (§7.5 da SPEC_035):
  - upstream api_backend → phicube-dashboard-api:8080
  - gzip compression
  - Cache strategy para index.html (must-revalidate) e assets (immutable, 1 ano)
  - Fallback para SPA: try_files $uri $uri/ /index.html
  - Proxy /api/* para api_backend
  - CORS headers
  - Health endpoint /health
  - Negar acesso a dotfiles (.git, ~backup)

**Artefatos:**
- `frontend/Dockerfile`
- `frontend/.dockerignore`
- `frontend/nginx.conf`

**Critério de Aceite:**
- ✅ `docker build -t phicube-frontend .` completa sem erros
- ✅ Imagem ~45MB (Node builder + nginx runtime)
- ✅ `docker run -p 3000:80 phicube-frontend` sobe e responde em :3000
- ✅ Acesso a http://localhost:3000/health retorna JSON
- ✅ Proxy `/api/*` funciona (testa com curl)

**Validador:** @coder  
**Revisado by:** @security-audit, @qa-review

---

### TASK_035_S3_09: docker-compose.yml Update & Healthcheck

**Tipo:** DevOps  
**Estimativa:** 30m  
**Dependências:** TASK_035_S3_08  
**Prioridade:** P1

**Descrição:**
- Atualizar `docker-compose.yml` na raiz do projeto:
  - Adicionar serviço `phicube-frontend`:
    - `build: context: ./frontend`
    - `container_name: phicube-frontend`
    - `ports: - "3000:80"`
    - `depends_on: - phicube-dashboard-api`
    - `environment: VITE_API_BASE_URL=/api/v1`
    - `healthcheck: wget --quiet --tries=1 --spider http://localhost/health`
    - `restart: unless-stopped`
    - `networks: - phicube-net`
  - **Gap crítico resolvido:** Mover Grafana de `:3000` para `:3001`
    - `ports: - "3001:3000"` (antes era 3000:3000)
  - Garantir que `phicube-frontend` depende de `phicube-dashboard-api`

**Artefatos:**
- `docker-compose.yml` (atualizado)

**Critério de Aceite:**
- ✅ `docker compose up -d` sobe frontend + API + MongoDB sem erros
- ✅ Frontend acessível em :3000
- ✅ Grafana acessível em :3001 (não mais em :3000)
- ✅ Healthcheck retorna success
- ✅ Proxy funciona: requests para /api chegam ao backend

**Validador:** @coder  
**Revisado by:** @security-audit, @qa-review

---

### TASK_035_S3_10: Bundle Size Validation & Performance

**Tipo:** QA  
**Estimativa:** 30m  
**Dependências:** TASK_035_S3_04  
**Prioridade:** P1

**Descrição:**
- Executar `npm run build` e verificar tamanho de cada chunk:
  - dist/index.html: < 10KB
  - dist/assets/main-*.css: < 10KB
  - dist/assets/app-*.js: < 30KB gzipped
  - dist/assets/vendor-*.js: < 50KB gzipped
  - Total gzipped: < 50KB (INV-035-07)
- Se exceder 50KB:
  - Analisar com `npm run build -- --analyze` (usando rollup-plugin-analyze)
  - Remover dependências não essenciais (ex: Chart.js se grande demais)
  - Otimizar imports (tree-shake)
- Documentar resultado em `frontend/PERFORMANCE.md`

**Artefatos:**
- `frontend/PERFORMANCE.md` (resultado da análise)

**Critério de Aceite:**
- ✅ Bundle gzipped < 50KB
- ✅ Build sem warnings críticos
- ✅ Documentação de performance gerada

**Validador:** @coder  
**Revisado by:** @qa-review

---

## Sprint 4: Documentação & Validação (0.5 dev-days)

### TASK_035_S4_01: README & DEVELOPMENT.md

**Tipo:** Documentation  
**Estimativa:** 2h  
**Dependências:** Todas as tasks anteriores  
**Prioridade:** P1

**Descrição:**
- Criar `frontend/README.md` com:
  - Título "Phicube Frontend SPA"
  - Seções:
    - Quick Start (npm install, npm run dev)
    - Build (npm run build)
    - Tests (npm run test)
    - Docker (docker build, docker compose)
    - Variáveis de ambiente (.env.local)
    - Tecnologias usadas
    - Links para docs (DEVELOPMENT.md, SPEC_035.md)
- Criar `frontend/DEVELOPMENT.md` com:
  - Padrões de componentização (props, emits, types)
  - Como estruturar nova view
  - Como usar Pinia store
  - Como adicionar nova rota
  - Exemplo prático: adicionar UtilCard componente
  - Testes: onde colocar, como estruturar
  - TypeScript strict: regras e exceções (se houver)

**Artefatos:**
- `frontend/README.md`
- `frontend/DEVELOPMENT.md`

**Critério de Aceite:**
- ✅ Docs completas, sem typos
- ✅ Exemplos de código funcionam
- ✅ Instruções de setup claras

**Validador:** @coder  
**Revisado by:** @qa-review

---

### TASK_035_S4_02: Validação QA — qa-review Skill

**Tipo:** Validation  
**Estimativa:** 1h  
**Dependências:** Todas as tasks anteriores  
**Prioridade:** P0

**Descrição:**
- Executar skill `@qa-review` checklist:
  - TypeScript strict sem erros: `npm run type-check`
  - Cobertura de testes ≥ 70%: `npm run test:coverage`
  - Bundle size < 50KB gzipped: `npm run build`
  - ESLint sem warnings críticos: `npm run lint`
  - Prettier formatado: `npm run format`
  - Testes passando: `npm run test`
- Documentar resultado em checklist DoD (§10.5)

**Artefatos:**
- Checklist QA preenchido

**Critério de Aceite:**
- ✅ Todos os items do QA checklist estão ✓
- ✅ Nenhum bloqueador crítico

**Validador:** @qa-review  
**Revisado by:** Líder técnico

---

### TASK_035_S4_03: Validação Security — security-audit Skill

**Tipo:** Validation  
**Estimativa:** 1h  
**Dependências:** Todas as tasks anteriores  
**Prioridade:** P0

**Descrição:**
- Executar skill `@security-audit` checklist:
  - Nenhuma API key hardcodada em código
  - Nenhum JWT em localStorage (apenas placeholder, será httpOnly em SPEC_036)
  - CSP headers em nginx.conf
  - npm audit: zero critical vulnerabilities
  - .env.* não commitado (.gitignore verifica)
  - Dependências npm sem malware (snyk check opcional)
- Documentar resultado

**Artefatos:**
- Checklist Security preenchido

**Critério de Aceite:**
- ✅ Nenhuma API key exposta
- ✅ CSP headers em nginx
- ✅ npm audit clean
- ✅ .gitignore protege .env*

**Validador:** @security-audit  
**Revisado by:** Líder técnico

---

### TASK_035_S4_04: Integração & Smoke Test em Docker Compose

**Tipo:** Validation  
**Estimativa:** 1h  
**Dependências:** TASK_035_S3_09  
**Prioridade:** P0

**Descrição:**
- Executar `docker compose down` (limpar)
- Executar `docker compose up -d` (subir stack completo)
- Aguardar healthchecks completarem (~10s)
- Testes de smoke:
  - GET http://localhost:3000/ retorna HTML index.html
  - GET http://localhost:3000/health retorna JSON status
  - GET http://localhost:3000/positions redireciona para / (SPA fallback)
  - GET http://localhost:3000/api/v1/positions (proxy) retorna JSON posições
  - Acesso http://localhost:3001 (Grafana) funciona
- Verificar logs: `docker compose logs phicube-frontend`
- Todos os health checks devem passar

**Artefatos:**
- Resultado de smoke tests documentado

**Critério de Aceite:**
- ✅ Frontend sobe sem erros
- ✅ API proxy funciona
- ✅ Grafana reulocado para :3001
- ✅ Health checks passam
- ✅ Sem erros nos logs

**Validador:** @coder, @qa-review  
**Revisado by:** Líder técnico

---

### TASK_035_S4_05: Finalização & Merge

**Tipo:** Administrative  
**Estimativa:** 30m  
**Dependências:** TASK_035_S4_04  
**Prioridade:** P0

**Descrição:**
- Verificar todos os itens de DoD (§10) preenchidos
- Atualizar `docs/SDD/SPEC_035_FRONTEND_FRAMEWORK/TASKS.md` com status final
- Executar skill `@sdd-spec-driven-development` validação:
  - User stories implementadas (US-035-01 a 05)
  - Invariantes respeitados (INV-035-01 a 08)
  - Compatibilidade com SPEC_002, SPEC_010, SPEC_036 validada
- Criar commit final (Conventional Commits):
  - `feat(frontend): implement SPEC_035 Vue.js SPA with Vite, Pinia, routing`
  - Body: referencia issue/PR, lista tasks completadas
- Push para branch principal (se workflow CI passar)

**Artefatos:**
- Commit final
- Validação SPEC completa

**Critério de Aceite:**
- ✅ Todos os items do DoD checklist estão ✓
- ✅ Commit criado com mensagem clara
- ✅ CI workflow passa (se configurado)
- ✅ SPEC_035 marcada como "Concluída"

**Validador:** @sdd-spec-driven-development  
**Revisado by:** Líder técnico

---

## 📊 Resumo de Tarefas

| Sprint | Fase | Tasks | Dias | Status |
|--------|------|-------|------|--------|
| **1** | Setup | S1_01 a S1_03 | 1.5 | ⏳ Pronto |
| **2** | Componentes & State | S2_01 a S2_06 | 3.5 | ⏳ Pronto |
| **3** | API, Testes & DevOps | S3_01 a S3_10 | 2.5 | ⏳ Pronto |
| **4** | Documentação & QA | S4_01 a S4_05 | 0.5 | ⏳ Pronto |
| **TOTAL** | | 21 tasks | 8.0 dev-days | ✅ Ready to Execute |

---

## 🎯 Critérios de Sucesso (DoD Final)

Ao concluir todas as tasks acima, SPEC_035 estará completa quando:

- ✅ Frontend SPA em Vue.js 3 com Vite rodando em localhost:3000
- ✅ 4 views + 404 com roteamento sem reload (SPA puro)
- ✅ 8 componentes reutilizáveis com TypeScript strict
- ✅ 3 Pinia stores gerenciando state global
- ✅ API service unificado com retry + 401 handling
- ✅ Testes: 70% cobertura mínima, todos passando
- ✅ Bundle < 50KB gzipped
- ✅ Dockerfile multi-stage (~45MB final)
- ✅ nginx.conf com proxy, CORS, cache strategy
- ✅ docker-compose.yml atualizado, Grafana em :3001
- ✅ Documentação completa (README, DEVELOPMENT.md)
- ✅ Validação QA, Security, SPEC completas

---

**Versão:** 2.0 Refinada  
**Data:** 2026-05-13  
**Autor:** OpenCode Task Decomposition  
**Status:** Pronto para Implementação ✅
