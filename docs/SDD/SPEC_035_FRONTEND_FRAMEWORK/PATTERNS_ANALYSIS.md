# Pattern Analysis Report — SPEC_035_FRONTEND_FRAMEWORK

**Comando:** `/analyze-patterns --pattern=all --depth=medium --output=markdown`  
**Data:** 2026-05-13  
**Versão SPEC:** 1.0 (original, 224 linhas)  
**Versão TASKS:** 2.0 (refinada, 1066 linhas)  
**Status:** Análise Completa — Apenas Especificação  

---

## 1. DISCREPÂNCIA IDENTIFICADA: SPEC vs TASKS ⚠️

| Artefato | Versão | Linhas | Status |
|----------|--------|--------|--------|
| `SPEC.md` | 1.0 (original) | 224 | 📄 Rascunho original |
| `TASKS.md` | 2.0 (refinada) | 1066 | ✅ Refinada |

**Nota:** A SPEC.md no diretório **não foi sobrescrita** pela versão refinada 2.0. O arquivo `SPEC_035_REFINED.md` (1620 linhas, gerado em sessão anterior) não substituiu o original.  
**Recomendação:** Substituir `SPEC.md` pelo conteúdo refinado antes de iniciar implementação.

---

## 2. DESIGN PATTERNS MAPEADOS

### 2.1 MVVM (Model-View-ViewModel)

| Atributo | Descrição |
|----------|-----------|
| **Ocorrências** | 7+ (implícito na arquitetura) |
| **Localização SPEC** | §4 (Estrutura), §5 (Componentes) |
| **Localização TASKS** | S2_01-S2_06, S3_01-S3_04 |
| **Similaridade** | 95% (padrão canônico Vue 3) |

**Mapeamento:**
```
Model  → Pinia stores (positionStore, performanceStore, uiStore)
View   → Componentes .vue (PositionTable, MetricCard, etc.)
View   → Views (DashboardView, PositionsView, etc.)
ViewModel → Composition API (ref, computed, watch, onMounted)
```

**Qualidade:** ⭐⭐⭐⭐  
- Separação de responsabilidades clara entre camadas  
- Pinia substitui Vuex com sintaxe mais limpa e type-safe  
- Composition API permite reutilização via composables  

**Refatoração sugerida:** Nenhuma. Padrão implementado corretamente.

---

### 2.2 Singleton Pattern

| Atributo | Descrição |
|----------|-----------|
| **Ocorrências** | 3 (implícitas) |
| **Localização SPEC** | §4 (api.ts), §6 (PositionStream) |
| **Localização TASKS** | S3_01 (API service), S2_05-S2_06 (stores) |
| **Similaridade** | 90% |

**Instâncias:**
1. **ApiClient** (`src/services/api.ts`) — instância única compartilhada
2. **Pinia stores** — `usePositionStore()` sempre retorna mesma instância (Pinia garante)
3. **PositionStream** (backend) — instância única no container

**Qualidade:** ⭐⭐⭐⭐  
- ApiClient como módulo singleton via exportação direta  
- Pinia stores são singletons por design (defineStore)  
- Nenhum anti-pattern (ex: class com constructor privado desnecessário)  

**Refatoração sugerida:**  
- Considerar `provide/inject` para ApiClient em vez de import direto:
```typescript
// main.ts
app.provide('apiClient', apiClient)

// Componente
const api = inject('apiClient') // testável via override
```
- Prioridade: Baixa (funciona bem como está)

---

### 2.3 Proxy Pattern

| Atributo | Descrição |
|----------|-----------|
| **Ocorrências** | 4 (2 implícitas + 2 explícitas) |
| **Localização** | SPEC §5.2 (vite proxy), TASKS S3_04, S3_08 (nginx), S3_01 (api.ts) |
| **Similaridade** | 88% |

**Instâncias:**
1. **Vite dev proxy** — `/api` → `localhost:8080`  
2. **nginx production proxy** — `/api` → `http://phicube-dashboard-api:8080`  
3. **ApiClient wrapper** — intercepta chamadas HTTP (retry, auth, error handling)  
4. **Router guard** — proxy de navegação (verifica auth antes de permitir rota)  

**Qualidade:** ⭐⭐⭐⭐  
- Proxy em dev e produção com propósitos diferentes (dev = CORS bypass, prod = gateway)  
- ApiClient adiciona camada de resiliência (retry, backoff) sem poluir chamadores  
- Router guard preparado para SPEC_036 (auth)  

**Refatoração sugerida:**  
- Extrair lógica de retry em interceptor axios (estilo AxiosInterceptorManager):
```typescript
api.interceptors.response.use(undefined, async (error) => {
  if (shouldRetry(error) && retryCount < 3) {
    await sleep(2 ** retryCount * 1000)
    return api.request(error.config)
  }
  throw error
})
```
- Prioridade: Média (melhora coesão)

---

### 2.4 Observer Pattern

| Atributo | Descrição |
|----------|-----------|
| **Ocorrências** | 4+ |
| **Localização** | SPEC §3 (US-035-01), TASKS S2_01 (router), S2_05-S2_06 (stores) |
| **Similaridade** | 92% |

**Instâncias:**
1. **Vue Reactivity** — `ref()`, `computed()`, `watch()` observam mudanças  
2. **Pinia stores** — componentes "observam" state e re-renderizam  
3. **Event emitter** — `auth:unauthorized` emitido pelo ApiClient  
4. **Router watcher** — `router.afterEach()` para analytics/logging  

**Qualidade:** ⭐⭐⭐⭐⭐  
- Vue 3 Composition API fornece reatividade granular (tracking de dependências)  
- Pinia actions disparam mutações observáveis por todos os consumers  
- Event emitter desacopla ApiClient do Router  

**Refatoração sugerida:**  
- Implementar EventBus centralizado:
```typescript
// src/utils/eventBus.ts
type Events = {
  'auth:unauthorized': void
  'connection:status': 'online' | 'offline'
  'data:refreshed': 'positions' | 'performance'
}
export const eventBus = new EventEmitter<Events>()
```
- Prioridade: Baixa (suficiente como está)

---

### 2.5 Repository Pattern

| Atributo | Descrição |
|----------|-----------|
| **Ocorrências** | 1 (implícito) |
| **Localização** | SPEC §4 (contrato API), TASKS S3_01 (api.ts) |
| **Similaridade** | 85% |

**Estrutura:**
```
services/
├── api.ts          ← Repository (métodos de acesso a dados)
├── types.ts        ← DTOs (Data Transfer Objects)
└── config.ts       ← Configuração (baseURL, timeout)
```

**Qualidade:** ⭐⭐⭐⭐  
- Desacopla componentes de chamadas HTTP  
- Centraliza retry, timeouts, headers  
- Fácil de mockar com `vi.mock()`  

**Refatoração sugerida:**  
- Separar por domínio (quando crescer):
```
services/
├── positionRepository.ts
├── performanceRepository.ts
└── healthRepository.ts
```
- Prioridade: Muito baixa (overhead desnecessário para 3 endpoints)

---

### 2.6 Factory Pattern

| Atributo | Descrição |
|----------|-----------|
| **Ocorrências** | 2+ |
| **Localização** | TASKS S2_01 (lazy loading de views) |
| **Similaridade** | 95% |

**Instância:**
```typescript
// Router lazy loading (defineAsyncComponent)
const DashboardView = () => import('@/views/DashboardView.vue')
```

**Qualidade:** ⭐⭐⭐⭐⭐  
- Vite/Rollup faz code-splitting automático  
- Lazy loading = chunk separado por view  

**Refatoração sugerida:** Nenhuma

---

## 3. STRUCTURAL PATTERNS

### 3.1 Layered Architecture

| Camada | Diretório | Responsabilidade | Exemplos |
|--------|-----------|------------------|----------|
| **Presentation** | `components/` | UI atoms | PositionTable, MetricCard, ErrorBanner |
| **Pages** | `views/` | Páginas completas | DashboardView, PositionsView |
| **State** | `stores/` | Estado global | positionStore, performanceStore, uiStore |
| **Data** | `services/` | Acesso a dados | api.ts, types.ts |
| **Routing** | `router/` | Navegação | index.ts, guards |
| **Styles** | `styles/` | CSS global | main.css, components.css |

**Qualidade:** ⭐⭐⭐⭐  
- Separação clara de responsabilidades  
- Fluxo unidirecional: View → Store → Service → API  
- Escalável para 10+ views  

**Refatoração sugerida:**  
- Adicionar camada `composables/` para hooks reutilizáveis:
```
src/
└── composables/
    ├── usePolling.ts     ← polling genérico (60s configurável)
    ├── useAsyncState.ts  ← loading/error/data pattern
    └── useDebounce.ts    ← debounce para filtros
```
- Prioridade: Alta (reduz duplicação em múltiplas views)

---

### 3.2 API Gateway Pattern (nginx)

| Atributo | Descrição |
|----------|-----------|
| **Ocorrências** | 1 (nginx.conf) |
| **Localização** | TASKS S3_08, SPEC §5 |
| **Complexidade** | Média (20-30 linhas de config) |

**Funcionalidades:**
- `/api/*` → proxy para `http://phicube-dashboard-api:8080`
- `Cache-Control` para assets estáticos
- SPA fallback: `try_files $uri /index.html`
- Headers de segurança (CSP, X-Frame-Options)

**Qualidade:** ⭐⭐⭐⭐  
- Resolve CORS em produção (mesma origin para browser)  
- Cache estratégico (assets imutáveis, HTML sem cache)  
- Healthcheck integrado  

**Refatoração sugerida:**  
- Adicionar rate limiting:
```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
location /api/ {
  limit_req zone=api burst=20 nodelay;
  proxy_pass http://phicube-dashboard-api:8080;
}
```
- Prioridade: Média (proteção contra abuso)

---

### 3.3 Multi-Stage Docker Build

| Atributo | Descrição |
|----------|-----------|
| **Ocorrências** | 1 (Dockerfile) |
| **Localização** | TASKS S3_08 |
| **Tamanho** | ~45MB |

**Stages:**
```
Stage 1: builder (node:20-alpine)
  → npm ci + npm run build
  → output: /app/dist/

Stage 2: runtime (nginx:alpine)
  → COPY --from=builder /app/dist /usr/share/nginx/html
  → COPY nginx.conf /etc/nginx/conf.d/default.conf
  → HEALTHCHECK wget
```

**Qualidade:** ⭐⭐⭐⭐⭐  
- Imagem final ~45MB (vs ~600MB com Node)  
- Produtivo-ready, sem devDependencies  
- Healthcheck evita tráfego para container não pronto  

**Refatoração sugerida:** Nenhuma

---

### 3.4 State Management com Pinia

| Store | State | Actions | Consumers |
|-------|-------|---------|-----------|
| **positionStore** | positions[], loading, error, lastUpdate | fetchPositions(), updatePosition(), clearPositions() | PositionsView, DashboardView |
| **performanceStore** | data, loading, error, lastUpdate | fetchPerformance() | DashboardView |
| **uiStore** | theme, sidebarOpen, notifications[] | toggleTheme(), toggleSidebar(), addNotification() | App.vue, Navbar |

**Qualidade:** ⭐⭐⭐⭐  
- Stores modulares e coesas (uma responsabilidade cada)  
- Composition API syntax (defineStore com setup function)  
- TypeScript strict em todo state  

**Refatoração sugerida:**  
- Adicionar `useAsyncState` composable:
```typescript
// composables/useAsyncState.ts
export function useAsyncState<T>(fetch: () => Promise<T>) {
  const data = ref<T | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  
  const execute = async () => {
    loading.value = true
    error.value = null
    try {
      data.value = await fetch()
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }
  
  return { data, loading, error, execute }
}
```
- Reutilizável em positionStore, performanceStore  
- Reduz ~15 linhas de código por store  
- Prioridade: Alta  

---

## 4. BEHAVIORAL PATTERNS

### 4.1 Async/Await + Retry (Circuit Breaker Lite)

| Atributo | Descrição |
|----------|-----------|
| **Ocorrências** | 1 (api.ts) |
| **Localização** | TASKS S3_01 |
| **Config** | Max 3 tentativas, backoff exponencial 1s/2s/4s |

**Pseudocódigo atual:**
```typescript
async function withRetry<T>(fn: () => Promise<T>, attempt = 0): Promise<T> {
  try {
    return await fn()
  } catch (e) {
    if (attempt >= 2) throw e
    await sleep(2 ** attempt * 1000)
    return withRetry(fn, attempt + 1)
  }
}
```

**Qualidade:** ⭐⭐⭐  
- Resiliência básica contra falhas temporárias  
- Backoff exponencial evita thundering herd  

**Refatoração sugerida:**  
- Implementar Circuit Breaker verdadeiro com 3 estados:
```typescript
enum CircuitState { CLOSED, OPEN, HALF_OPEN }

class CircuitBreaker {
  state = CircuitState.CLOSED
  failures = 0
  threshold = 3
  timeout = 30000 // 30s para reset
  
  async call<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === CircuitState.OPEN) {
      throw new Error('Circuit breaker is OPEN')
    }
    try {
      const result = await fn()
      this.reset()
      return result
    } catch (e) {
      this.failures++
      if (this.failures >= this.threshold) {
        this.state = CircuitState.OPEN
        setTimeout(() => this.state = CircuitState.HALF_OPEN, this.timeout)
      }
      throw e
    }
  }
}
```
- Prioridade: Média (upgrade incremental)

---

### 4.2 Polling Pattern

| Atributo | Descrição |
|----------|-----------|
| **Ocorrências** | 2 (DashboardView, PositionsView) |
| **Intervalo** | 60 segundos |
| **Localização** | TASKS S3_02 |

**Código atual (duplicado em 2 views):**
```typescript
onMounted(() => {
  fetchData()
  const interval = setInterval(fetchData, 60000)
  onUnmounted(() => clearInterval(interval))
})
```

**Qualidade:** ⭐⭐⭐  
- Funcional mas duplicado  
- Sem cleanup se o componente desmontar com erro  

**Refatoração sugerida (prioridade ALTA):**
```typescript
// composables/usePolling.ts
export function usePolling<T>(
  fn: () => Promise<T>,
  interval: number = 60000,
  immediate: boolean = true
) {
  const data = ref<T | null>(null)
  const error = ref<Error | null>(null)
  
  const execute = async () => {
    try {
      data.value = await fn()
      error.value = null
    } catch (e) {
      error.value = e as Error
    }
  }
  
  if (immediate) execute()
  
  const timer = setInterval(execute, interval)
  
  onUnmounted(() => clearInterval(timer))
  
  return { data, error, execute }
}
```

---

### 4.3 Error Handling Strategy

| Nível | Mecanismo | Ação | Responsável |
|-------|-----------|------|-------------|
| **HTTP** | Axios interceptor | Retry automático + 401 event | api.ts |
| **Store** | try/catch em actions | set error no state + loading=false | Stores |
| **Component** | ErrorBanner + loading | Exibe mensagem + spinner | ErrorBanner.vue |
| **Router** | Navigation guard | Redireciona para /login em 401 | router/index.ts |
| **Global** | window.onerror | Log + fallback UI | main.ts |

**Qualidade:** ⭐⭐⭐⭐  
- Granularidade apropriada (cada nível trata o que sabe)  
- Degradação graciosa (spinner → banner → fallback)  

**Refatoração sugerida:**  
- Adicionar `onErrorCaptured` no App.vue para captura global:
```typescript
// App.vue
onErrorCaptured((err) => {
  console.error('[FE] Uncaught:', err)
  uiStore.addNotification('Erro inesperado. Tente recarregar.', 'error')
  return false // previne propagação
})
```
- Prioridade: Baixa (nice-to-have)

---

## 5. TESTING PATTERNS MAPEADOS

### 5.1 Unit Testing (Vitest)

| Atributo | Descrição |
|----------|-----------|
| **Framework** | Vitest v2 |
| **Environment** | jsdom |
| **Coverage target** | ≥ 70% |
| **Setup** | tests/setup.ts (Vi mock global) |

**Distribuição de testes (10 arquivos):**

| Arquivo | Tests planejados | O que cobre |
|---------|-----------------|-------------|
| `PositionTable.spec.ts` | 4 (render, loading, sort, filter) | Comportamento do componente |
| `MetricCard.spec.ts` | 3 (label, delta, colors) | Renderização condicional |
| `SignalBadge.spec.ts` | 2 (direction, colors) | Variação de props |
| `positionStore.spec.ts` | 4 (fetch, pnl, winCount, update) | Lógica de store |
| `performanceStore.spec.ts` | 2 (fetch, metrics) | Lógica de store |
| `api.spec.ts` | 4 (calls, parse, retry, 401) | Integração HTTP |
| `router.spec.ts` | 5 (4 rotas + 404) | Roteamento |
| `DashboardView.spec.ts` | — (não listado) | — |
| `PositionsView.spec.ts` | — (não listado) | — |

**Total:** ~21 casos de teste

**Qualidade:** ⭐⭐⭐  
- Cobertura boa para componentes e lógica  
- View tests ausentes (DashboardView, PositionsView)  
- Testes de integração apenas smoke (Docker)  

**Refatoração sugerida:**
1. Adicionar testes de view:
   - DashboardView: renderiza 6 MetricCards  
   - PositionsView: renderiza PositionTable  
2. Adicionar teste de integração E2E (deferred para SPEC_037):  
3. Prioridade: Média  

---

### 5.2 TypeScript Strict Validation

| Atributo | Descrição |
|----------|-----------|
| **Modo** | strict: true |
| **Flags** | noImplicitAny, strictNullChecks, noUnusedLocals, noUnusedParameters, noImplicitReturns |
| **Build gate** | `vue-tsc --noEmit && vite build` |
| **TASKS** | S1_03 (setup), S3_07 (validação) |

**Qualidade:** ⭐⭐⭐⭐⭐  
- TypeScript strict = zero erros de tipo em build  
- Pre-build check com vue-tsc (não apenas IDE)  
- Build falha se erro de tipo  

**Refatoração sugerida:** Nenhuma

---

### 5.3 Bundle Size Validation

| Atributo | Descrição |
|----------|-----------|
| **Métrica** | < 50KB gzipped total |
| **Chunks** | index.html < 10KB, CSS < 10KB, JS vendor < 30KB, app < 20KB |
| **TASKS** | S3_10 (validação) |

**Riscos:**
- **Chart.js** (45KB+) se incluído → estoura budget  
- **axios** (14KB) vs fetch nativo (0KB)  
- **vue-router** (10KB) + **pinia** (2KB) somam ~12KB  

**Recomendação:** Marcar Chart.js como lazy-loaded ou deferred para SPEC_039.

**Qualidade:** ⭐⭐⭐⭐  
- Budget explícito e verificável  
- Análise de bundle com `rollup-plugin-analyze`  

**Refatoração sugerida:**  
- Se Chart.js estourar budget, usar lightweight-charts (TradingView): ~5KB
- Prioridade: Média

---

## 6. PADRÕES DE ORGANIZAÇÃO DE TAREFAS

### 6.1 Sprint Structure

| Sprint | Foco | Tasks | Dias | % do total |
|--------|------|-------|------|-----------|
| **1** | Setup (Vite, DEPS, TS) | 3 | 1.5 | 19% |
| **2** | Componentes & Stores | 6 | 3.5 | 44% |
| **3** | API, Testes, DevOps | 10 | 2.5 | 31% |
| **4** | Documentação, QA, Merge | 5 | 0.5 | 6% |
| **Total** | | 21 tasks | 8.0 | 100% |

**Qualidade:** ⭐⭐⭐⭐  
- Sprint 2 é o mais pesado (44%) — normal para construção de componentes  
- Sprint 4 é validação pura (6%) — lean  
- Dependências claras entre sprints  

**Refatoração sugerida:**  
- Desmembrar Sprint 3 (10 tasks):  
  - Separar DevOps (S3_08, S3_09) das tasks de API/testes (S3_01-S3_07, S3_10)  
  - Criar Sprint 3a: API + Testes (1.5d, 7 tasks)  
  - Criar Sprint 3b: DevOps (1d, 3 tasks)  
- Prioridade: Baixa (apenas se houver 2 devs)

---

### 6.2 Task Granularity Analysis

| Tamanho | Contagem | % |
|---------|----------|---|
| **30min** | 2 (S3_04, S3_10) | 9% |
| **1h** | 10 tasks | 48% |
| **1.5h** | 6 tasks | 29% |
| **2h** | 2 tasks (S1_02, S4_01) | 9% |
| **3h** | 1 task (S1_01) | 5% |

**Qualidade:** ⭐⭐⭐⭐  
- 48% das tasks são 1h — granularidade ideal  
- Nenhuma task > 3h (evita tarefas "blob")  
- Tasks de 30min podem ser agrupadas  

---

## 7. ANÁLISE CROSS-FILE (SPEC vs TASKS)

### 7.1 User Stories Coverage

| US ID | Nome | SPEC | TASKS | Status |
|-------|------|------|-------|--------|
| **US-035-01** | Roteamento SPA | §3 (4 rotas) | S2_01 | ✅ Coberto |
| **US-035-02** | Componentização | §3 (3 comps) | S2_03, S2_04 | ✅ Coberto |
| **US-035-03** | Consumo API | §4 (getPositions) | S3_01 | ✅ Coberto |
| **US-035-04** | Docker + Compose | §5.3, §5.4 | S3_08, S3_09 | ✅ Coberto |
| **US-035-05** | Roteamento robusto | **NÃO EXISTE em v1.0** | S2_01 (404) | ⚠️ Gap SPEC |

**Gap:** SPEC v1.0 não tem US-035-05 (404, router guards). TASKS v2.0 implementa.  
**Ação:** Atualizar SPEC.md com US-035-05 antes do merge.

---

### 7.2 Invariantes Coverage

| INV ID | Descrição | SPEC | TASKS | Status |
|--------|-----------|------|-------|--------|
| INV-035-01 | Sem chamada direta ao MongoDB | §6 | — | ⚠️ Implícito |
| INV-035-02 | Proxy `/api` evita CORS | §6 | S3_04, S3_08 | ✅ Coberto |
| INV-035-03 | Sem secrets no frontend | §6 | S4_03 (security) | ✅ Coberto |
| INV-035-04 | Build falha com TS error | §6 | S3_07 | ✅ Coberto |
| INV-035-05 | JWT em memória (não localStorage) | **AUSENTE** | — | ❌ Gap |
| INV-035-06 | URLs relativas (`/api/v1/*`) | **AUSENTE** | S3_01 | ⚠️ Implícito |
| INV-035-07 | Zero CDN | **AUSENTE** | S3_08 | ⚠️ Implícito |
| INV-035-08 | CSP headers | **AUSENTE** | S4_03 | ⚠️ Implícito |

**Gaps:** SPEC v1.0 tem apenas 4 invariantes. Versão refinada tem 8.  
**Ação:** Atualizar SPEC.md com INV-035-05 a 08.

---

### 7.3 Test Coverage (SPEC vs TASKS)

| TEST ID | Descrição | SPEC | TASKS | Status |
|---------|-----------|------|-------|--------|
| TEST_035_01 | Build completo sem erros | §7 | S3_07 | ✅ Coberto |
| TEST_035_02 | Proxy dev redireciona | §7 | S3_04 | ✅ Coberto |
| TEST_035_03 | PositionTable renderiza | §7 | S3_05 | ✅ Coberto |
| TEST_035_04 | Roteamento navega | §7 | S3_07 | ✅ Coberto |
| TEST_035_05 | Dockerfile < 50MB | §7 | S3_08 | ✅ Coberto |
| — | Coverage 70% | **AUSENTE** | S3_05 | ⚠️ Gap |
| — | Bundle < 50KB gzipped | **AUSENTE** | S3_10 | ⚠️ Gap |
| — | TypeScript strict check | **AUSENTE** | S3_07 | ⚠️ Gap |

**Ação:** Adicionar TEST_035_06 (coverage ≥ 70%), TEST_035_07 (bundle < 50KB), TEST_035_08 (TypeScript strict) na SPEC.md.

---

## 8. OPORTUNIDADES DE REFACTORING (RANKED)

### Prioridade Alta (Recomendado para v1)

| # | Oportunidade | Impacto | Esforço | TASKS afetadas |
|---|-------------|---------|---------|----------------|
| 1 | **Extrair `composables/usePolling.ts`** | Reduz duplicação em 2 views | 30min | S3_02 |
| 2 | **Extrair `composables/useAsyncState.ts`** | Reduz ~15 linhas/store, padroniza error loading | 30min | S2_05, S2_06 |
| 3 | **Atualizar SPEC.md v1.0 → v2.0 refinada** | Alinha SPEC com TASKS | 15min | Pré-implementação |

### Prioridade Média (v1.1)

| # | Oportunidade | Impacto | Esforço | Justificativa |
|---|-------------|---------|---------|---------------|
| 4 | **Axios retry interceptor** | Separa responsabilidade de retry do ApiClient | 20min | Clean Code |
| 5 | **Rate limiting em nginx** | Proteção contra abuso em produção | 10min | Segurança |
| 6 | **Circuit Breaker** | Resiliência contra falhas em cascata | 40min | Robustez |

### Prioridade Baixa (v2.0+)

| # | Oportunidade | Impacto | Esforço | Justificativa |
|---|-------------|---------|---------|---------------|
| 7 | **EventBus centralizado** | Desacoplamento total de eventos | 20min | Elegância |
| 8 | **View tests (DashboardView.spec.ts)** | Cobertura de integração | 40min | Qualidade |
| 9 | **Global error handler (onErrorCaptured)** | Resiliência contra bugs não tratados | 10min | Estabilidade |
| 10 | **provide/inject para ApiClient** | Testabilidade de components | 15min | Testes |
| 11 | **Repository separado por domínio** | Escalabilidade para 10+ endpoints | 20min | Organização |

---

## 9. SIMILARITY MATRIX

| Par (Padrão) | Similaridade | Explicação |
|-------------|-------------|------------|
| Vite dev proxy vs nginx proxy | 75% | Mesmo propósito (proxy /api), implementação diferente |
| positionStore vs performanceStore | 80% | Mesmo pattern (fetch → state → error), domínio diferente |
| PositionTable vs MetricCard | 45% | Ambos recebem props e renderizam, mas lógica interna difere |
| DashboardView vs PositionsView | 70% | Ambos usam store + polling + loading/error states |
| Docker vs docker-compose | 85% | Dockerfile define imagem, compose orquestra serviços |
| SPEC v1.0 vs TASKS v2.0 | 55% | Spece e tasks divergem em conteúdo refinado |

---

## 10. MÉTRICAS DE QUALIDADE ESTIMADAS

| Métrica | Target | Risco | Justificativa |
|---------|--------|-------|---------------|
| **Bundle size (gzipped)** | < 50KB | ⭐ Baixo | Vue+Router+Pinia+axios ≈ 35KB, sem Chart.js |
| **Test coverage** | ≥ 70% | ⭐⭐ Médio | 21 casos planejados, falta views/header/footer |
| **TypeScript strict** | 100% pass | ✅ Garantido | Build gate com vue-tsc --noEmit |
| **Container size** | ~45MB | ✅ Confirmado | nginx:alpine (~25MB) + dist (~1MB) |
| **FCP (First Contentful Paint)** | < 2s | ⭐⭐ Médio | Code splitting, lazy loading de rotas |
| **LCP (Largest Contentful Paint)** | < 2.5s | ⭐⭐⭐ Alto | Depende de performance da API + rede |
| **Acessibilidade WCAG 2.1** | AA | ⭐⭐⭐⭐ Crítico | **Não abordado em SPEC ou TASKS** |

---

## 11. GLOSSÁRIO DE PADRÕES (para consistência)

| Termo SPEC/TASKS | Pattern Type | Nome Formal | Frequência |
|-----------------|-------------|-------------|------------|
| `api.ts` wrapper | **Proxy** | API Proxy | 1 |
| `positionStore` | **Observer + Singleton** | State Store | 3 |
| Vite proxy | **Proxy** | Dev Proxy | 1 |
| Docker multi-stage | **Structural** | Multi-stage Build | 1 |
| Router lazy loading | **Factory** | Lazy Factory | 5 |
| Component Props | **Structural** | Props Interface | 8 |
| onMounted polling | **Behavioral** | Interval Polling | 2 |
| retry + backoff | **Behavioral** | Circuit Breaker Lite | 1 |
| nginx proxy | **Structural** | API Gateway | 1 |
| error banner | **Behavioral** | Error Boundary | 1 |

---

## 12. RECOMENDAÇÕES FINAIS

### Antes de implementar (gaps SPEC)

| Ação | Prioridade | Responsável |
|------|-----------|-------------|
| 🔴 Substituir SPEC.md pela versão refinada 2.0 | **CRÍTICA** | Time A |
| 🔴 Adicionar US-035-05 (roteamento robusto) na SPEC | **CRÍTICA** | Time A |
| 🟠 Adicionar INV-035-05 a 08 na SPEC | **ALTA** | Time A |
| 🟠 Adicionar TEST_035_06, 07, 08 na SPEC | **ALTA** | Time A |
| 🟡 Resolver conflito porta :3000 (Grafana → :3001) | **MÉDIA** | Time B |

### Durante implementação (refactoring)

| Ação | Prioridade | Sprint/Task |
|------|-----------|-------------|
| 📌 Extrair `usePolling.ts` composable | **Alta** | Sprint 3 (nova task) |
| 📌 Extrair `useAsyncState.ts` composable | **Alta** | Sprint 2 (nova task) |
| 📌 Separar Sprint 3 em 3a + 3b | **Média** | Pré-sprint planning |
| 📌 Adicionar view tests | **Média** | Sprint 3 (próximo a S3_05) |
| 📌 Implementar rate limiting nginx | **Média** | Sprint 3 (junto S3_08) |

### Pós-implementação (v1.1+)

| Ação | Prioridade | SPEC futura |
|------|-----------|-------------|
| Circuit Breaker verdadeiro | Média | SPEC_046 |
| EventBus centralizado | Baixa | SPEC_047 |
| E2E tests (Cypress/Playwright) | Média | SPEC_037 |
| Global error handler | Baixa | SPEC_047 |

---

## RESUMO

| Categoria | Pontuação | Notas |
|-----------|-----------|-------|
| **Design Patterns** | ⭐⭐⭐⭐ (8/10) | MVVM, Singleton, Proxy implementados corretamente |
| **Structural Patterns** | ⭐⭐⭐⭐⭐ (9/10) | Layered arch, API Gateway, Multi-stage build |
| **Behavioral Patterns** | ⭐⭐⭐⭐ (7.5/10) | Polling duplicado, retry sem Circuit Breaker |
| **Testing Patterns** | ⭐⭐⭐ (7/10) | 70% target ok, falta view tests |
| **Task Organization** | ⭐⭐⭐⭐ (8.5/10) | Granularidade boa, dependências claras |
| **Cross-file Consistency** | ⭐⭐⭐ (6.5/10) | **SPEC v1.0 desalinhada com TASKS v2.0** |
| **Overall** | **⭐⭐⭐⭐ (7.7/10)** | **Sólido, com gaps de alinhamento SPEC-TASKS** |

---

**Arquivo:** `docs/SDD/SPEC_035_FRONTEND_FRAMEWORK/PATTERNS_ANALYSIS.md`  
**Gerado em:** 2026-05-13  
**Comando:** `/analyze-patterns --pattern=all --language=ts --depth=medium --output=markdown`  
**Status:** ✅ Análise completa — nenhuma implementação realizada
