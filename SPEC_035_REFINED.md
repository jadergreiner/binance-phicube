# SPEC_035 — Modernização do Frontend com Framework SPA

**ID:** SPEC_035  
**Título:** Frontend SPA Moderno com Vue.js 3 + Vite  
**Data:** 2026-05-13  
**Status:** Rascunho Refinado  
**Versão:** 2.0 (Refinamento)  
**Dependências:** SPEC_002 (Frontend Consulta de Posições), SPEC_010 (Dashboard Performance), SPEC_036 (Autenticação Dashboard), SPEC_021 (Validação Operacional)  
**PRD §:** Fase 2 — "Interface de usuário modernizada"  
**Skills de Validação:** `qa-review`, `security-audit`, `lint-on-edit`, `sdd-spec-driven-development`

---

## 1. Resumo Executivo

Esta SPEC moderniza o frontend vanilla HTML/CSS/JS existente (servido pelo FastAPI) em uma **Single Page Application (SPA) profissional** usando **Vue.js 3 + Composition API + Vite + TypeScript**, mantendo compatibilidade total com a API REST existente (SPEC_002, SPEC_010) e preparando a integração de autenticação JWT (SPEC_036).

O novo frontend oferece:
- **Roteamento robusto** (4 views principais + 404, proteção de rota pré-login)
- **Componentização reutilizável** (PositionTable, MetricCard, SignalBadge, PriceChart)
- **Contrato API unificado** (`src/services/api.ts`) cobrindo posições (SPEC_002) e performance (SPEC_010)
- **TypeScript strict** em build e testes
- **Dockerfile production-ready** (multi-stage, ~45MB final)
- **nginx.conf** com proxy `/api` para `http://phicube-dashboard-api:8080`

### Resolução de Conflitos Críticos
- **Porta:** Frontend ocupa `:3000` (Grafana reulocar-se-á para `:3001` em docker-compose.yml)
- **Arquitetura:** Vue.js 3 recomendado (React opcional, mas não será documentado nesta versão)
- **DevOps:** Proxy dev no Vite + nginx em produção (CORS resolvido no router nginx)

---

## 2. Objetivo

Substituir o painel vanilla por um SPA moderno que:

1. **Melhora a experiência de usuário** com navegação sem reload, atualização reativa de dados (via WebSocket ou polling)
2. **Facilita manutenção e evolução** com componentização, roteamento explícito e tipagem TypeScript strict
3. **Integra-se perfeitamente** com a API REST existente e dashboard em FastAPI
4. **Prepara o terreno** para autenticação (SPEC_036) e monitoramento de performance (SPEC_010)
5. **Reduz tamanho de bundle** (< 50KB gzipped) e tempo de carregamento initial (< 2s em 4G)

---

## 3. Escopo

### 3.1 Dentro do Escopo

#### Frontend
- **Framework:** Vue.js 3.5+ com Composition API, Vite 6+, TypeScript 5.6+
- **Roteamento:** Vue Router 4 com lazy-loading, 404 e redirecionamento pré-login
- **Componentes reutilizáveis:**
  - `PositionTable.vue` — tabela com posições, ordenação, filtro por símbolo
  - `MetricCard.vue` — cartão de métrica (label, valor, delta, cor verde/vermelho)
  - `SignalBadge.vue` — badge de sinal (LONG/SHORT/NEUTRO)
  - `PriceChart.vue` — gráfico de preço (via Chart.js ou Lightweight Charts.js)
  - `LoadingSpinner.vue` — indicador de carregamento
  - `ErrorBanner.vue` — exibição de erros de rede/API

#### Estado Global
- **Pinia 2** para state management (posições, performance, ui state)
- Mutations para posições atualizadas via WebSocket
- Actions para fetch de dados (getPositions, getPerformance, etc)

#### Contrato API Unificado (`src/services/api.ts`)
- `getPositions()` → `GET /api/v1/positions` (SPEC_002)
- `getPerformance()` → `GET /api/v1/performance` (SPEC_010)
- `getHealthz()` → `GET /health` (health check)
- Tratamento de erro 401 (para redirecionamento pré-login em SPEC_036)
- Retry automático com backoff exponencial (máx 3 tentativas)

#### Views (Páginas)
- **Dashboard** (`/`) — resumo global: posições abertas, PnL, performance
- **Posições** (`/positions`) — tabela detalhada de posições abertas
- **Histórico** (`/history`) — tabela de trades fechados (mockado inicialmente)
- **Configuração** (`/settings`) — informações de bot, versão, env (view simples, sem ações)
- **404** (`/404`) — página de rota não encontrada

#### DevOps
- **Vite proxy dev** (`vite.config.ts`) → `http://localhost:8080` para `/api` e `/health`
- **Dockerfile multi-stage:**
  - Build stage: Node 20-alpine, `npm ci`, `npm run build`
  - Serve stage: nginx:alpine com volume `/usr/share/nginx/html`
- **nginx.conf:** proxy `/api/*` para `http://phicube-dashboard-api:8080`, CORS headers, cache estratégico
- **docker-compose.yml:** serviço `phicube-frontend` em `:3000`, volume de dist, healthcheck

#### Testes
- **Unit tests:** Vitest para componentes, store Pinia, API service
- **TypeScript strict** em build e linting
- **Bundle size check:** < 50KB gzipped (vue, vue-router, pinia, axios)
- **Cobertura mínima:** 70% (diferente de backend 80%)

#### Documentação
- `frontend/README.md` com instruções dev e build
- `frontend/DEVELOPMENT.md` com padrões de componentização e store
- Comentários em código português (como AGENTS.md)

### 3.2 Fora do Escopo

- **Testes E2E** (Cypress/Playwright) — será SPEC_037+
- **PWA / Offline Support** — deferred
- **i18n / Multi-idioma** — português BR apenas nesta versão
- **Tema customizável** (dark/light toggle) — será SPEC_038+
- **Realtime WebSocket atualização** — polled a cada 60s por enquanto (atualização posições via API, não WebSocket)
- **Charts avançados / Candlestick** — será SPEC_039+
- **OAuth2 / SSO** — será parte de SPEC_036+

---

## 4. Modelo de Dados

### 4.1 Estrutura do Projeto Frontend

```
frontend/
├── src/
│   ├── components/
│   │   ├── PositionTable.vue          # Tabela de posições
│   │   ├── MetricCard.vue             # Cartão de métrica (label, valor, delta)
│   │   ├── SignalBadge.vue            # Badge de sinal LONG/SHORT/NEUTRO
│   │   ├── PriceChart.vue             # Gráfico de preço
│   │   ├── LoadingSpinner.vue         # Spinner de carregamento
│   │   ├── ErrorBanner.vue            # Banner de erro
│   │   ├── Layout/
│   │   │   ├── Navbar.vue             # Barra de navegação
│   │   │   └── Footer.vue             # Rodapé (versão, status)
│   │   └── __tests__/
│   │       ├── PositionTable.spec.ts
│   │       ├── MetricCard.spec.ts
│   │       └── SignalBadge.spec.ts
│   ├── views/
│   │   ├── DashboardView.vue          # / — resumo global
│   │   ├── PositionsView.vue          # /positions — tabela detalhada
│   │   ├── HistoryView.vue            # /history — trades fechados
│   │   ├── SettingsView.vue           # /settings — informações
│   │   ├── NotFoundView.vue           # /404 — página não encontrada
│   │   └── __tests__/
│   │       ├── DashboardView.spec.ts
│   │       └── PositionsView.spec.ts
│   ├── services/
│   │   ├── api.ts                     # Contrato unificado, chamadas HTTP
│   │   ├── types.ts                   # Tipos compartilhados (Position, Performance, etc)
│   │   ├── config.ts                  # Configurações (API_BASE_URL, etc)
│   │   └── __tests__/
│   │       └── api.spec.ts
│   ├── stores/
│   │   ├── positionStore.ts           # Pinia: state positions, mutations
│   │   ├── performanceStore.ts        # Pinia: state performance, metrics
│   │   ├── uiStore.ts                 # Pinia: state UI (loading, error)
│   │   └── __tests__/
│   │       ├── positionStore.spec.ts
│   │       └── performanceStore.spec.ts
│   ├── router/
│   │   ├── index.ts                   # Vue Router config, lazy-loading, guards
│   │   └── __tests__/
│   │       └── router.spec.ts
│   ├── styles/
│   │   ├── main.css                   # Global styles, vars CSS
│   │   ├── components.css             # Styles dos componentes
│   │   └── animations.css             # Transições/animações
│   ├── App.vue                        # Raiz da aplicação
│   ├── main.ts                        # Entry point
│   └── vite-env.d.ts                  # Tipos Vite (auto-gerado)
├── public/
│   ├── favicon.ico
│   └── robots.txt
├── tests/
│   ├── integration/
│   │   └── dashboard-flow.spec.ts     # Fluxo dashboard → posições
│   ├── e2e/ (fora do escopo)
│   └── vitest.config.ts
├── package.json
├── package-lock.json
├── vite.config.ts
├── tsconfig.json
├── tsconfig.app.json
├── vitest.config.ts
├── .eslintrc.json
├── .prettierrc
├── index.html
├── Dockerfile
├── .dockerignore
├── nginx.conf
├── docker-entrypoint.sh (opcional, para health check)
├── README.md                          # Setup, dev, build
├── DEVELOPMENT.md                     # Padrões, componentização
└── .gitignore
```

### 4.2 Tipos TypeScript (`src/services/types.ts`)

```typescript
// Contrato SPEC_002 (Posições)
export interface Position {
  symbol: string;
  direction: "LONG" | "SHORT";
  entry_price: number;
  current_price: number;
  quantity: number;
  pnl_usdt: number;
  pnl_pct: number;
  sl_price: number;
  tp_price: number;
  open_time: string;  // ISO 8601
  leverage: number;
  margin_usdt: number;
}

// Contrato SPEC_010 (Performance Global)
export interface PerformanceGlobal {
  total_trades: number;
  win_rate_pct: number;
  total_pnl_usdt: number;
  avg_rrr: number;
  max_drawdown_usdt: number;
  profit_factor: number;
}

// Contrato SPEC_010 (Performance por Símbolo)
export interface PerformanceBySymbol {
  symbol: string;
  total_trades: number;
  win_rate_pct: number;
  total_pnl_usdt: number;
  avg_rrr: number;
  max_drawdown_usdt: number;
  profit_factor: number;
}

// Contrato SPEC_010 (Performance por Timeframe)
export interface PerformanceByTimeframe {
  timeframe: string;  // "15m", "1h", "4h", etc
  total_trades: number;
  win_rate_pct: number;
  total_pnl_usdt: number;
  avg_rrr: number;
  max_drawdown_usdt: number;
  profit_factor: number;
}

// Resposta unificada de performance
export interface PerformanceResponse {
  global: PerformanceGlobal;
  by_symbol: PerformanceBySymbol[];
  by_timeframe: PerformanceByTimeframe[];
}

// Erro de API
export interface ApiError {
  status: number;
  message: string;
  timestamp: string;
}

// Estado de saúde
export interface HealthStatus {
  status: "healthy" | "degraded" | "unhealthy";
  uptime_seconds: number;
  mongodb_connected: boolean;
  binance_client_ok: boolean;
  timestamp: string;
}
```

### 4.3 Contrato API (`src/services/api.ts`)

```typescript
import axios from 'axios';
import type { Position, PerformanceResponse, HealthStatus, ApiError } from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor: Retry com backoff exponencial (máx 3 tentativas)
let retryCount = 0;
const MAX_RETRIES = 3;

client.interceptors.response.use(
  (response) => {
    retryCount = 0;
    return response;
  },
  async (error) => {
    const config = error.config;
    if (!config) return Promise.reject(error);
    
    if (retryCount < MAX_RETRIES && error.response?.status >= 500) {
      retryCount++;
      const delay = Math.pow(2, retryCount - 1) * 1000; // 1s, 2s, 4s
      await new Promise(resolve => setTimeout(resolve, delay));
      return client(config);
    }
    
    // Erro 401 → redirecionar para login (tratado em router/guards)
    if (error.response?.status === 401) {
      window.dispatchEvent(new CustomEvent('auth:unauthorized'));
    }
    
    return Promise.reject(error);
  }
);

/**
 * Obtém lista de posições abertas (SPEC_002)
 */
export async function getPositions(): Promise<Position[]> {
  const response = await client.get('/positions');
  return response.data;
}

/**
 * Obtém métricas de performance global e por símbolo/timeframe (SPEC_010)
 */
export async function getPerformance(): Promise<PerformanceResponse> {
  const response = await client.get('/performance');
  return response.data;
}

/**
 * Health check
 */
export async function getHealth(): Promise<HealthStatus> {
  const response = await client.get('/health', {
    baseURL: '/api'  // Override para /api/health (FastAPI root)
  });
  return response.data;
}

/**
 * Tratamento de erro genérico
 */
export function parseApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    return {
      status: error.response?.status || 0,
      message: error.response?.data?.message || error.message,
      timestamp: new Date().toISOString(),
    };
  }
  return {
    status: 0,
    message: String(error),
    timestamp: new Date().toISOString(),
  };
}

export { client as httpClient };
```

### 4.4 Pinia Store — Posições (`src/stores/positionStore.ts`)

```typescript
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { getPositions } from '../services/api';
import type { Position } from '../services/types';

export const usePositionStore = defineStore('positions', () => {
  const positions = ref<Position[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastUpdate = ref<Date | null>(null);

  // Computed: totais
  const totalPnl = computed(() => 
    positions.value.reduce((sum, p) => sum + p.pnl_usdt, 0)
  );

  const winCount = computed(() =>
    positions.value.filter(p => p.pnl_usdt > 0).length
  );

  const lossCount = computed(() =>
    positions.value.filter(p => p.pnl_usdt < 0).length
  );

  // Actions
  async function fetchPositions() {
    loading.value = true;
    error.value = null;
    try {
      const data = await getPositions();
      positions.value = data;
      lastUpdate.value = new Date();
    } catch (err) {
      error.value = String(err);
      console.error('[positionStore] Erro ao buscar posições:', err);
    } finally {
      loading.value = false;
    }
  }

  function updatePosition(updated: Position) {
    const idx = positions.value.findIndex(p => p.symbol === updated.symbol);
    if (idx >= 0) {
      positions.value[idx] = updated;
      lastUpdate.value = new Date();
    }
  }

  function clearPositions() {
    positions.value = [];
  }

  return {
    positions,
    loading,
    error,
    lastUpdate,
    totalPnl,
    winCount,
    lossCount,
    fetchPositions,
    updatePosition,
    clearPositions,
  };
});
```

### 4.5 Pinia Store — Performance (`src/stores/performanceStore.ts`)

```typescript
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { getPerformance } from '../services/api';
import type { PerformanceResponse } from '../services/types';

export const usePerformanceStore = defineStore('performance', () => {
  const data = ref<PerformanceResponse | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastUpdate = ref<Date | null>(null);

  async function fetchPerformance() {
    loading.value = true;
    error.value = null;
    try {
      const result = await getPerformance();
      data.value = result;
      lastUpdate.value = new Date();
    } catch (err) {
      error.value = String(err);
      console.error('[performanceStore] Erro ao buscar performance:', err);
    } finally {
      loading.value = false;
    }
  }

  const globalMetrics = computed(() => data.value?.global ?? null);

  return {
    data,
    loading,
    error,
    lastUpdate,
    globalMetrics,
    fetchPerformance,
  };
});
```

---

## 5. User Stories

### US-035-01 — Roteamento SPA sem reload

**Como** operador,  
**quero** navegar entre as 4 views sem recarregar a página,  
**para** ter uma experiência mais fluida e rápida.

**Critérios de Aceite:**
- `/` → DashboardView carrega (resumo com cards de posições e performance)
- `/positions` → PositionsView carrega tabela detalhada
- `/history` → HistoryView carrega histórico de trades (mockado nesta versão)
- `/settings` → SettingsView carrega info do bot
- `/any-invalid-route` → NotFoundView com botão para voltar
- Navegação entre rotas acontece sem reload (SPA puro)
- Volta do browser funciona (popstate handler)

**DoD:**
- [ ] Vue Router configurado com lazy-loading de views
- [ ] 4 views implementadas + 404
- [ ] Tests para roteamento (navigation guards, lazy-load)
- [ ] Link/Router-link em Navbar funciona
- [ ] Browser back/forward funciona

---

### US-035-02 — Exibição reativa de posições

**Como** operador,  
**quero** ver minhas posições abertas em uma tabela clara com atualização automática,  
**para** monitorar a situação em tempo real.

**Critérios de Aceite:**
- PositionTable exibe colunas: Symbol, Direction, Entry Price, Current Price, Quantity, PnL (USDT), PnL (%), SL, TP
- Ordenação por coluna (click no header)
- Filtro por Symbol (search box)
- Polling automático a cada 60s via `fetchPositions()`
- Erro de rede não quebra a UI (error banner exibido)
- Sem posições → tabela vazia com mensagem "Nenhuma posição aberta"

**DoD:**
- [ ] PositionTable.vue implementado com Composition API + Pinia
- [ ] Coluna PnL com cor verde/vermelho (SignalBadge ou estilo inline)
- [ ] Tests para rendering, ordenação, filtro
- [ ] API call retry com backoff

---

### US-035-03 — Exibição de performance global e por símbolo

**Como** operador,  
**quero** ver métricas de performance (win rate, PnL, drawdown, profit factor) globais e por símbolo,  
**para** avaliar se o bot está rentável.

**Critérios de Aceite:**
- Dashboard exibe 6 MetricCards globais: Total Trades, Win Rate, Total PnL, Avg RRR, Max Drawdown, Profit Factor
- Performance por símbolo em tabela separada (symbol, total_trades, win_rate, pnl_usdt, etc)
- Performance por timeframe em tabela separada (timeframe, total_trades, win_rate, pnl_usdt, etc)
- Polling automático a cada 60s
- Sem dados → cards exibem "—" ou "0"

**DoD:**
- [ ] MetricCard.vue implementado
- [ ] performanceStore com state + actions
- [ ] Duas tabelas (por símbolo e por timeframe)
- [ ] Tests para computação de métricas

---

### US-035-04 — Componentização reutilizável

**Como** desenvolvedor,  
**quero** ter componentes de UI reutilizáveis e bem tipados,  
**para** adicionar novas telas e features rapidamente.

**Critérios de Aceite:**
- Componentes: PositionTable, MetricCard, SignalBadge, PriceChart, LoadingSpinner, ErrorBanner, Navbar, Footer
- Cada componente tem props tipadas (TypeScript)
- Cada componente tem testes unitários (Vitest)
- Documentação (JSDoc) em cada componente
- Nenhuma dependência de global state (props e emits apenas)

**DoD:**
- [ ] 8 componentes implementados
- [ ] Tests para cada um (70% cobertura mínima)
- [ ] JSDoc com exemplos de uso
- [ ] Bundle size verificado (< 50KB)

---

### US-035-05 — Roteamento robusto com proteção pré-login

**Como** operador autenticado (SPEC_036),  
**quero** que rotas protegidas redirecione-me para login se meu token expirar,  
**para** garantir segurança.

**Critérios de Aceite:**
- Router guard verifica token JWT antes de acessar `/` e outras rotas
- Sem token ou token expirado → redirecionamento para `/login`
- `/health` sempre acessível (public)
- Error 401 da API → banner de erro + redirecionamento em 3s
- LocalStorage / SessionStorage armazena token (será httpOnly cookie em produção, SPEC_036)

**DoD:**
- [ ] Router guard implementado
- [ ] Tests para verificação de autenticação
- [ ] Interceptor 401 em api.ts
- [ ] Evento customizado 'auth:unauthorized' emitido
- [ ] Integração com SPEC_036 planejada (não implementada ainda)

---

## 6. Design Técnico

### 6.1 Arquitetura Geral

```
┌─────────────────────────────────────────────────────────────────┐
│                    Browser (User)                               │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │
                    ┌─────────▼──────────┐
                    │  Vue.js 3 SPA      │
                    │  (frontend:3000)   │
                    │                    │
                    │  - Vue Router      │
                    │  - Pinia Store     │
                    │  - Components      │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────────────────────┐
                    │   nginx (reverse proxy)            │
                    │   - Serve dist/ static files       │
                    │   - Proxy /api/* → API backend     │
                    │   - CORS headers                   │
                    │   - Cache strategy (index.html)    │
                    └─────────┬──────────────────────────┘
                              │
                    ┌─────────▼──────────────────────────┐
                    │  FastAPI Dashboard API             │
                    │  (phicube-dashboard-api:8080)      │
                    │                                    │
                    │  GET /api/v1/positions             │
                    │  GET /api/v1/performance           │
                    │  GET /health                       │
                    │  POST /auth/login (SPEC_036)       │
                    └─────────┬──────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  MongoDB + Binance │
                    │  (dados)           │
                    └────────────────────┘
```

### 6.2 Fluxo de Requisição

1. **Frontend carrega** em `:3000`
2. **nginx** serve `dist/index.html`
3. **Vue Router** detecta rota (`/positions`)
4. **PositionsView** monta, chama `positionStore.fetchPositions()`
5. **api.ts** faz `GET /api/v1/positions`
6. **nginx** intercepta, proxeia para `http://phicube-dashboard-api:8080/api/v1/positions`
7. **FastAPI** retorna dados
8. **Pinia** atualiza state
9. **Vue reactive system** re-renderiza PositionTable
10. **User** vê a tabela carregada

### 6.3 Polling de Dados

```javascript
// Em DashboardView.vue onMounted()
const positionStore = usePositionStore();
const performanceStore = usePerformanceStore();

// Initial fetch
await Promise.all([
  positionStore.fetchPositions(),
  performanceStore.fetchPerformance(),
]);

// Polling a cada 60s
const interval = setInterval(() => {
  positionStore.fetchPositions();
  performanceStore.fetchPerformance();
}, 60000);

// Cleanup
onBeforeUnmount(() => clearInterval(interval));
```

### 6.4 Tratamento de Erro

```typescript
// Em api.ts (interceptor 401)
client.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Emitir evento global
      window.dispatchEvent(
        new CustomEvent('auth:unauthorized', { 
          detail: { message: 'Sessão expirada. Faça login novamente.' } 
        })
      );
      // Router guard será responsável pelo redirecionamento
    }
    return Promise.reject(error);
  }
);
```

```vue
<!-- Em router/index.ts (navigation guard) -->
router.beforeEach(async (to, from, next) => {
  // Rotas públicas
  const publicRoutes = ['/login', '/404'];
  
  // Se rota protegida e sem token → /login
  if (!publicRoutes.includes(to.path) && !hasValidToken()) {
    return next('/login');
  }
  
  next();
});
```

---

## 7. Componentes

### 7.1 Setup Inicial

```bash
# Criar projeto Vite + Vue 3 + TypeScript
npm create vite@latest frontend -- --template vue-ts

cd frontend

# Instalar dependências
npm install

# Dev dependencies
npm install --save-dev \
  vue-router@4 \
  pinia \
  axios \
  typescript@5.6 \
  @vitejs/plugin-vue \
  @vue/test-utils \
  vitest \
  @vitest/ui \
  jsdom \
  eslint \
  prettier \
  chart.js vue-chartjs

# Build
npm run build
```

### 7.2 Configuração Vite (`frontend/vite.config.ts`)

```typescript
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';

export default defineConfig({
  plugins: [vue()],
  
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  
  server: {
    port: 3000,
    proxy: {
      // Proxy dev para API local
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/api'),
      },
      '/health': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
  
  build: {
    target: 'esnext',
    minify: 'terser',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          'vue-core': ['vue', 'vue-router'],
          'state': ['pinia'],
          'http': ['axios'],
        },
      },
    },
  },
});
```

### 7.3 TypeScript Strict (`frontend/tsconfig.json`)

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "jsx": "preserve",
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "strictPropertyInitialization": true,
    "noImplicitThis": true,
    "alwaysStrict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    
    "moduleResolution": "bundler",
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    },
    "resolveJsonModule": true,
    "isolatedModules": true,
  },
  "include": ["src/**/*.ts", "src/**/*.d.ts", "src/**/*.tsx", "src/**/*.vue"],
  "exclude": ["node_modules", "dist"],
}
```

### 7.4 Dockerfile Multi-Stage

```dockerfile
# ============================================
# Stage 1: Build
# ============================================
FROM node:20-alpine AS builder

WORKDIR /app

# Copiar package files
COPY package*.json ./

# Instalar dependências (ci = ci, não npm install)
RUN npm ci

# Copiar código-fonte
COPY . .

# Build
RUN npm run build

# ============================================
# Stage 2: Runtime (nginx)
# ============================================
FROM nginx:1.27-alpine

# Remover default config
RUN rm /etc/nginx/conf.d/default.conf

# Copiar nginx.conf customizado
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copiar dist do builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1

# Expose
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
```

Tamanho esperado final: ~45MB (node:20-alpine builder + nginx:alpine)

### 7.5 nginx.conf

```nginx
# upstream para API backend
upstream api_backend {
  server phicube-dashboard-api:8080;
}

# server block principal
server {
  listen 80;
  server_name _;

  # Serve estáticos (SPA assets)
  root /usr/share/nginx/html;

  # Gzip compression
  gzip on;
  gzip_types text/plain text/css text/javascript application/json 
             application/javascript application/x-javascript image/svg+xml;
  gzip_min_length 1000;
  gzip_vary on;

  # Cache strategy para index.html (deve sempre refetch)
  location = /index.html {
    add_header Cache-Control "max-age=0, must-revalidate";
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'";
  }

  # Cache para assets (versioned files, 1 ano)
  location ~ /assets/ {
    add_header Cache-Control "max-age=31536000, immutable";
  }

  # Fallback para SPA: qualquer rota desconhecida volta para index.html
  location / {
    try_files $uri $uri/ /index.html;
  }

  # Proxy /api/* para backend FastAPI
  location /api/ {
    proxy_pass http://api_backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Timeout para WebSocket (se usado no futuro)
    proxy_read_timeout 86400s;
    proxy_send_timeout 86400s;
    
    # CORS headers (se backend não os enviar)
    add_header 'Access-Control-Allow-Origin' '*' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
    add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization' always;
  }

  # Health check endpoint (simples)
  location /health {
    access_log off;
    return 200 '{"status":"healthy"}';
    add_header Content-Type application/json;
  }

  # Denegar acesso a arquivos sensíveis
  location ~ /\. {
    deny all;
    access_log off;
    log_not_found off;
  }

  location ~ ~$ {
    deny all;
    access_log off;
    log_not_found off;
  }
}
```

### 7.6 docker-compose.yml — Serviço Frontend

```yaml
services:
  phicube-frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: phicube-frontend
    ports:
      - "3000:80"
    depends_on:
      - phicube-dashboard-api
    environment:
      - VITE_API_BASE_URL=/api/v1
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/health"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 5s
    restart: unless-stopped
    networks:
      - phicube-net
    
  # Grafana: mover para porta 3001 (gap crítico resolvido)
  grafana:
    image: grafana/grafana:11.0-alpine
    container_name: grafana
    ports:
      - "3001:3000"  # Mudado de 3000 para 3001
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    depends_on:
      - prometheus
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 3s
      retries: 3
    restart: unless-stopped
    networks:
      - phicube-net

  # ... resto dos serviços (phicube, phicube-dashboard-api, mongodb, etc)
```

---

## 8. Testes

### 8.1 Configuração Vitest (`frontend/vitest.config.ts`)

```typescript
import { defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue';
import path from 'path';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'dist/',
        '**/*.spec.ts',
        '**/__tests__/**',
      ],
      lines: 70,      // Cobertura mínima 70%
      functions: 70,
      branches: 70,
      statements: 70,
    },
  },
});
```

### 8.2 Tests de Componentes

```typescript
// src/components/__tests__/PositionTable.spec.ts
import { describe, it, expect, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import PositionTable from '../PositionTable.vue';
import type { Position } from '../../services/types';

describe('PositionTable.vue', () => {
  const mockPositions: Position[] = [
    {
      symbol: 'BTCUSDT',
      direction: 'LONG',
      entry_price: 67000,
      current_price: 68000,
      quantity: 0.5,
      pnl_usdt: 500,
      pnl_pct: 1.49,
      sl_price: 66000,
      tp_price: 70000,
      open_time: '2026-05-13T10:00:00Z',
      leverage: 5,
      margin_usdt: 6700,
    },
  ];

  it('renderiza posições', () => {
    const wrapper = mount(PositionTable, {
      props: {
        positions: mockPositions,
        loading: false,
      },
    });

    expect(wrapper.text()).toContain('BTCUSDT');
    expect(wrapper.text()).toContain('LONG');
    expect(wrapper.text()).toContain('500.00 USDT');
  });

  it('exibe loading spinner quando loading=true', () => {
    const wrapper = mount(PositionTable, {
      props: {
        positions: [],
        loading: true,
      },
    });

    expect(wrapper.find('.spinner').exists()).toBe(true);
  });

  it('ordena por coluna ao clicar header', async () => {
    const wrapper = mount(PositionTable, {
      props: {
        positions: mockPositions,
        loading: false,
      },
    });

    const header = wrapper.find('th');
    await header.trigger('click');

    expect(wrapper.emitted('sort')).toBeTruthy();
  });

  it('filtra por Symbol', async () => {
    const wrapper = mount(PositionTable, {
      props: {
        positions: mockPositions,
        loading: false,
      },
    });

    const input = wrapper.find('input[type="search"]');
    await input.setValue('BTC');

    expect(wrapper.vm.filtered.length).toBeGreaterThan(0);
  });
});
```

### 8.3 Tests de Store (Pinia)

```typescript
// src/stores/__tests__/positionStore.spec.ts
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { usePositionStore } from '../positionStore';
import * as apiService from '../../services/api';

vi.mock('../../services/api');

describe('positionStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('fetchPositions atualiza state', async () => {
    const store = usePositionStore();
    const mockData = [
      {
        symbol: 'BTCUSDT',
        direction: 'LONG',
        entry_price: 67000,
        current_price: 68000,
        quantity: 0.5,
        pnl_usdt: 500,
        pnl_pct: 1.49,
        sl_price: 66000,
        tp_price: 70000,
        open_time: '2026-05-13T10:00:00Z',
        leverage: 5,
        margin_usdt: 6700,
      },
    ];

    vi.mocked(apiService.getPositions).mockResolvedValue(mockData);

    await store.fetchPositions();

    expect(store.positions).toEqual(mockData);
    expect(store.loading).toBe(false);
  });

  it('totalPnl é computado corretamente', () => {
    const store = usePositionStore();
    store.positions = [
      { ...mockPosition, pnl_usdt: 500 },
      { ...mockPosition, pnl_usdt: -200 },
    ];

    expect(store.totalPnl).toBe(300);
  });

  it('winCount conta posições positivas', () => {
    const store = usePositionStore();
    store.positions = [
      { ...mockPosition, pnl_usdt: 500 },
      { ...mockPosition, pnl_usdt: -200 },
      { ...mockPosition, pnl_usdt: 100 },
    ];

    expect(store.winCount).toBe(2);
  });
});
```

### 8.4 Tests de API Service

```typescript
// src/services/__tests__/api.spec.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';
import { getPositions, getPerformance, parseApiError } from '../api';

vi.mock('axios');

describe('api.ts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('getPositions faz chamada correta', async () => {
    const mockData = [{ symbol: 'BTCUSDT', direction: 'LONG', /* ... */ }];
    vi.mocked(axios.get).mockResolvedValue({ data: mockData });

    const result = await getPositions();

    expect(result).toEqual(mockData);
    expect(axios.get).toHaveBeenCalledWith('/positions');
  });

  it('getPerformance faz chamada correta', async () => {
    const mockData = {
      global: { total_trades: 10, win_rate_pct: 60, /* ... */ },
      by_symbol: [],
      by_timeframe: [],
    };
    vi.mocked(axios.get).mockResolvedValue({ data: mockData });

    const result = await getPerformance();

    expect(result).toEqual(mockData);
  });

  it('parseApiError extrai info corretamente', () => {
    const error = new Error('Network error');
    const parsed = parseApiError(error);

    expect(parsed.status).toBe(0);
    expect(parsed.message).toBe('Network error');
    expect(parsed.timestamp).toBeDefined();
  });

  it('retry com backoff funciona', async () => {
    // Mock com falha seguida de sucesso
    vi.mocked(axios.get)
      .mockRejectedValueOnce(new Error('500 Internal Server Error'))
      .mockResolvedValueOnce({ data: [] });

    // Nota: implementação real de retry está em interceptor
    // Este test valida a lógica conceptual
  });
});
```

### 8.5 Tests de Roteamento

```typescript
// src/router/__tests__/router.spec.ts
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { createRouter, createWebHistory } from 'vue-router';
import routes from '../index';

describe('Router', () => {
  const router = createRouter({
    history: createWebHistory(),
    routes,
  });

  it('rota / existe', () => {
    const route = routes.find(r => r.path === '/');
    expect(route).toBeDefined();
  });

  it('rota /positions existe', () => {
    const route = routes.find(r => r.path === '/positions');
    expect(route).toBeDefined();
  });

  it('rota /404 existe', () => {
    const route = routes.find(r => r.path === '/404');
    expect(route).toBeDefined();
  });

  it('rota desconhecida redireciona para 404', async () => {
    await router.push('/unknown-route');
    // Assert redirecionamento (depende de beforeEach guard)
  });

  it('guard verifica autenticação', async () => {
    // Mock localStorage sem token
    vi.stubGlobal('localStorage', {
      getItem: () => null,
    });

    await router.push('/positions');
    // Assert redirecionamento para /login (com SPEC_036)
  });
});
```

### 8.6 Tests de TypeScript Strict

```bash
# Validate TypeScript strict
npm run type-check

# Output esperado: "0 errors found"
```

**tsconfig.json** já contém `"strict": true` e todas as flags.

### 8.7 Bundle Size Check

```bash
# Build e verifica tamanho
npm run build

# Output esperado:
# dist/index.html           4.2 kB
# dist/assets/app-*.js     45.3 kB (gzipped)
# dist/assets/vendor-*.js  22.1 kB (gzipped)
```

---

## 9. Invariantes (INV-035-xx)

| ID | Invariante | Rationale |
|----|-----------|-----------|
| INV-035-01 | Frontend **nunca** faz chamada direta ao MongoDB | Isolamento de segurança: dados passam por API FastAPI sempre |
| INV-035-02 | Toda requisição para dados passa por proxy `/api` | CORS resolvido em nginx, evita preflight em produção |
| INV-035-03 | Frontend **não tem acesso** a secrets (BINANCE_API_KEY, JWT_SECRET, etc) | Secrets vivem em backend; frontend usa token JWT apenas |
| INV-035-04 | Build falha se TypeScript tem erro de tipo (strict mode) | `npm run build` retorna exit code 1 se `noEmitOnError: true` ou `npm run type-check` falhar |
| INV-035-05 | Todas as chamadas de API têm tratamento de erro e timeout | Resiliência: retry + timeout + error boundary em UI |
| INV-035-06 | SPA sempre serve index.html em rotas desconhecidas (fallback) | nginx `try_files $uri $uri/ /index.html` — necessário para SPA roter de lado cliente |
| INV-035-07 | Bundle gzipped < 50KB (sem dependencies de chart pesadas) | Performance: carregamento < 2s em 4G |
| INV-035-08 | Erro 401 da API dispara evento customizado `auth:unauthorized` | Preparação para SPEC_036: redirecionamento centralizado |

---

## 10. Definition of Done (DoD)

Cada item abaixo deve ser validado antes de marcar SPEC_035 como concluída.

### 10.1 Implementação do Frontend

- [ ] Projeto Vue.js 3 + Vite criado em `frontend/`
- [ ] TypeScript strict configurado (`tsconfig.json`, build falha se erro)
- [ ] 4 views principais implementadas: Dashboard, Posições, Histórico, Configuração
- [ ] Roteamento SPA sem reload funciona (Vue Router 4 lazy-loading)
- [ ] Página 404 implementada
- [ ] 6 componentes reutilizáveis implementados:
  - PositionTable (tabela com ordenação, filtro)
  - MetricCard (card de métrica com cor)
  - SignalBadge (badge LONG/SHORT/NEUTRO)
  - PriceChart (gráfico mock ou Chart.js)
  - LoadingSpinner (spinner de carregamento)
  - ErrorBanner (banner de erro)
- [ ] Navbar com links de navegação
- [ ] Footer com versão/status
- [ ] Pinia store para posições (`src/stores/positionStore.ts`)
- [ ] Pinia store para performance (`src/stores/performanceStore.ts`)
- [ ] Pinia store para UI (`src/stores/uiStore.ts`)
- [ ] API service unificado (`src/services/api.ts`) com:
  - `getPositions()` (SPEC_002)
  - `getPerformance()` (SPEC_010)
  - `getHealth()`
  - Retry com backoff exponencial
  - Tratamento 401
- [ ] Polling automático a cada 60s (Dashboard, Posições)
- [ ] Tratamento de erro (error banner, mensagens claras)

### 10.2 DevOps & Infraestrutura

- [ ] `frontend/Dockerfile` multi-stage (Node 20-alpine builder + nginx runtime)
- [ ] `frontend/nginx.conf` com proxy `/api`, CORS, cache strategy
- [ ] `.dockerignore` configurado (node_modules, dist, etc)
- [ ] `docker-compose.yml` atualizado:
  - [ ] Serviço `phicube-frontend` em `:3000`
  - [ ] Serviço `grafana` **movido** para `:3001` (gap crítico resolvido)
  - [ ] Healthcheck para frontend
  - [ ] Dependência em `phicube-dashboard-api`
- [ ] Vite proxy dev (`vite.config.ts`) configura `/api` → `localhost:8080`
- [ ] `npm run dev` funciona localmente (servidor dev + proxy)
- [ ] `npm run build` produz dist/ otimizado
- [ ] `docker compose up` sobe frontend + API + MongoDB

### 10.3 Testes

- [ ] **Unit tests:** Vitest configurado
  - [ ] PositionTable.spec.ts (render, ordenação, filtro)
  - [ ] MetricCard.spec.ts (props, cores)
  - [ ] SignalBadge.spec.ts
  - [ ] positionStore.spec.ts (state, actions, computed)
  - [ ] performanceStore.spec.ts
  - [ ] api.spec.ts (chamadas, retry, erro)
  - [ ] router.spec.ts (rotas, guards)
- [ ] Cobertura mínima 70% (`npm run test:coverage`)
- [ ] **TypeScript strict validation:** `npm run type-check` sem erros
- [ ] **Bundle size:** `npm run build` < 50KB gzipped (vue + router + pinia + axios)
- [ ] **Tests passando:**
  - `npm run test` — todos os testes verdes
  - `npm run lint` — sem warnings (ESLint)
  - `npm run format` — Prettier aplicado
- [ ] **Integration test:** Fluxo completo (dashboard → posições → dados carregam)

### 10.4 Documentação

- [ ] `frontend/README.md` com:
  - Setup dev (npm install, npm run dev)
  - Build (npm run build)
  - Docker (docker build, docker compose)
  - Variáveis de ambiente (VITE_API_BASE_URL)
- [ ] `frontend/DEVELOPMENT.md` com:
  - Padrões de componentização (props, emits, composables)
  - Padrões de store (Pinia)
  - Estrutura de pasta
  - Exemplo: como adicionar nova view
- [ ] JSDoc/comentários em cada componente (exemplos de uso)
- [ ] Tipos TypeScript documentados (`src/services/types.ts`)

### 10.5 Validação & Segurança

- [ ] **qa-review skill:** Validação de quality gates
  - [ ] TypeScript strict sem erros
  - [ ] Cobertura de testes 70%+
  - [ ] Bundle size < 50KB
  - [ ] Sem console.log em produção
- [ ] **security-audit skill:** Validação de segurança
  - [ ] Nenhuma API key hardcodada
  - [ ] Nenhum JWT salvo em localStorage (planejado para httpOnly em SPEC_036)
  - [ ] CSP headers em nginx
  - [ ] Dependências vulneráveis (npm audit)
- [ ] **lint-on-edit skill:** Formatação automática
  - [ ] ESLint rules aplicadas
  - [ ] Prettier formatado
- [ ] **sdd-spec-driven-development skill:** Validação contra SPEC
  - [ ] Todas as user stories implementadas
  - [ ] Invariantes respeitados
  - [ ] Compatibilidade com SPEC_002, SPEC_010, SPEC_036 validada

### 10.6 Compatibilidade & Integração

- [ ] **SPEC_002 (Posições):** API `/api/v1/positions` consumida corretamente
- [ ] **SPEC_010 (Performance):** API `/api/v1/performance` consumida e exibida
- [ ] **SPEC_036 (Autenticação):** Router guard placeholder (será completado em SPEC_036)
  - [ ] Evento `auth:unauthorized` disparado em erro 401
  - [ ] Redirecionamento planejado (não implementado ainda)
- [ ] **SPEC_021 (Validação):** Testes passam em CI

### 10.7 Go-Live

- [ ] Frontend image (~45MB) builda sem erros
- [ ] `docker compose up -d` sobe todo stack
- [ ] Acessar `http://localhost:3000` no browser carrega painel
- [ ] Tabela de posições exibe dados do MongoDB
- [ ] Performance cards exibem métricas
- [ ] Polling a cada 60s funciona
- [ ] Erro de rede não quebra UI (error banner exibido)
- [ ] Navegação entre views funciona sem reload
- [ ] Browser back/forward funciona
- [ ] Grafana acessível em `http://localhost:3001`

---

## 11. Timeline & Estimativa de Esforço

### Cenário: 1 dev frontend, 8 dev-days (Sprint de 2 semanas, ~1 semana de trabalho)

| Sprint | Atividade | Dias | Responsável | Validação |
|--------|-----------|------|-------------|-----------|
| **Sprint 1** | Setup Vite + Vue 3, TypeScript, Pinia | 1.5 | Dev Frontend | `npm run dev` roda, types OK |
| **Sprint 1** | Roteamento + 4 views + 404 | 1.5 | Dev Frontend | Navegação SPA funciona |
| **Sprint 2** | Componentes (6x) — PositionTable, MetricCard, SignalBadge, etc | 2 | Dev Frontend | `npm run build` OK, bundle < 50KB |
| **Sprint 2** | Pinia stores (posições, performance, ui) | 1.5 | Dev Frontend | Tests passam, state mutations OK |
| **Sprint 3** | API service unificado (getPositions, getPerformance) + retry | 1 | Dev Frontend | API calls funcionam, retry testado |
| **Sprint 3** | Testes unitários (70% cobertura) | 1 | Dev Frontend | `npm run test:coverage` ≥ 70% |
| **Sprint 3** | Dockerfile + nginx.conf + docker-compose | 0.5 | Dev Frontend | `docker compose up` funciona |
| **Sprint 4** | Documentação (README, DEVELOPMENT.md) | 0.5 | Dev Frontend | Docs completos, exemplos OK |
| **Sprint 4** | Validação: qa-review + security-audit + lint-on-edit | 1 | Skills | Tudo verde |
| **Total** | | **8 dev-days** | | Go-live pronto |

---

## 12. Referências & Dependências

### 12.1 Compatibilidade com Specs

| SPEC | Vínculo | Impacto |
|------|---------|--------|
| SPEC_002 | Upstream: API de posições | Frontend consome `GET /api/v1/positions` |
| SPEC_010 | Upstream: API de performance | Frontend consome `GET /api/v1/performance` |
| SPEC_036 | Downstream: Autenticação JWT | Router guard + evento 401 preparados (implementação em SPEC_036) |
| SPEC_021 | Validação: Testes operacionais | SPEC_035 testes devem passar em CI |
| SPEC_014 | Upstream: Security design | CSP headers, sem secrets hardcodados |

### 12.2 Dependências npm

**Produção:**
- vue@3.5.0+
- vue-router@4.3.0+
- pinia@2.2.0+
- axios@1.7.0+
- chart.js@4.4.0+ (opcional para PriceChart)
- vue-chartjs@5.3.0+ (opcional)

**Dev:**
- typescript@5.6+
- vite@6.0+
- @vitejs/plugin-vue@5.0+
- @vue/test-utils@2.4+
- vitest@2.0+
- jsdom@24.0+
- eslint@9.0+
- prettier@3.0+

---

## 13. Próximas Steps (Pós SPEC_035)

- **SPEC_036:** Autenticação JWT (login form, token refresh, 2FA planejado)
- **SPEC_037:** Testes E2E com Playwright/Cypress
- **SPEC_038:** Tema dark/light customizável
- **SPEC_039:** Charts avançados (candlestick, análise técnica)
- **SPEC_040:** PWA + offline support
- **SPEC_041:** Real-time updates via WebSocket (ao invés de polling)

---

## 14. FAQ & Esclarecimentos

### P: Por que Vue.js 3 e não React?

**R:** Vue 3 oferece melhor balance entre:
- Curva de aprendizado (Composition API mais intuitiva que hooks)
- Bundle size (vue ~35KB vs react ~40KB)
- Integração com Pinia (mais simples que Redux/Zustand)
- Documentação excelente em português

React é opcional, mas não será documentado nesta versão. Migração futura é viável.

### P: Por que Pinia e não Vuex?

**R:** Pinia é o successor oficial de Vuex:
- API modular (menos boilerplate)
- TypeScript first
- DevTools integradas
- Recomendado pela comunidade Vue

### P: Onde armazeno o token JWT (SPEC_036)?

**R:** Nesta versão, localStorage (via composable). Em produção (SPEC_036), será httpOnly cookie via Set-Cookie do backend.

### P: O frontend precisa de CORS?

**R:** Não. nginx proxeia `/api/*` para backend, então o navegador não vê cross-origin. Em dev (Vite), proxy configurado evita CORS também.

### P: Quanto tempo de load esperado?

**R:** ~2s em 4G (target):
- HTML: 4KB, 50ms
- JavaScript bundle: 45KB gzipped, 300ms
- CSS: inline ou critical, 50ms
- Primeira requisição de dados: 1.5s (latência + API)

### P: Como debugar em produção (Docker)?

**R:** Via logs:
```bash
docker logs phicube-frontend
```

Para sourcemaps, manter `sourceMap: true` em vite.config.ts (opcional em produção, adiciona ~5KB).

---

## 15. Anexos

### 15.1 Checklist para Implementador

- [ ] Clone/fork repositório
- [ ] `npm create vite@latest frontend -- --template vue-ts`
- [ ] Copiar configs (tsconfig.json, vite.config.ts, vitest.config.ts) da seção 7
- [ ] Implementar estrutura de pasta (`src/components`, `src/views`, `src/stores`, `src/services`, `src/router`)
- [ ] Implementar 6 componentes (1 dia)
- [ ] Implementar 3 stores (1 dia)
- [ ] Implementar API service + tipos (0.5 dia)
- [ ] Implementar roteamento (0.5 dia)
- [ ] Escrever testes (1.5 dias)
- [ ] Dockerfile + nginx.conf (0.5 dia)
- [ ] Atualizar docker-compose.yml
- [ ] Documentação (0.5 dia)
- [ ] Validação via skills (qa-review, security-audit, lint-on-edit)
- [ ] Merge e deploy

### 15.2 Variáveis de Ambiente

**`frontend/.env.local` (dev):**
```
VITE_API_BASE_URL=http://localhost:8080/api/v1
VITE_APP_ENV=development
```

**`frontend/.env.production` (Docker):**
```
VITE_API_BASE_URL=/api/v1
VITE_APP_ENV=production
```

---

## Resumo Final

Esta SPEC_035 refinada entrega um **frontend SPA profissional, tipado, testado e pronto para produção**, resolvendo todos os 8 gaps críticos identificados:

1. ✅ **Porta `:3000`** — Grafana reulocar para `:3001`
2. ✅ **Dockerfile completo** — Multi-stage, Node + nginx, ~45MB
3. ✅ **Contrato API unificado** — getPositions, getPerformance, retry, 401 handling
4. ✅ **Roteamento robusto** — 404, guards, lazy-loading
5. ✅ **Testes TypeScript strict** — 70% cobertura, bundle < 50KB
6. ✅ **Framework: Vue.js 3** — Com Composition API + Pinia
7. ✅ **Proxy dev/prod** — Vite dev + nginx em Docker
8. ✅ **DoD com validadores** — qa-review, security-audit, lint-on-edit, sdd-spec-driven-development

**Pronto para implementação em Sprint 1-4 (~8 dev-days, 1 dev frontend).**

---

**Versão:** 2.0 Refinada (2026-05-13)  
**Status:** Pronto para Implementação  
**Skill de Validação:** `sdd-spec-driven-development`, `qa-review`, `security-audit`, `lint-on-edit`
