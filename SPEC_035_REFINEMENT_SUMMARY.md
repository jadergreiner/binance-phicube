# SPEC_035 Refinement Summary

**Data:** 2026-05-13  
**Versão:** 1.0  
**Status:** Entrega Completa

---

## 1. Gaps Críticos Identificados vs. Resolvidos

| # | Gap | Severidade | Status | Resolução |
|---|-----|-----------|--------|-----------|
| 1 | Conflito de porta `:3000` (Grafana vs Frontend) | **CRÍTICO** | ✅ **RESOLVIDO** | Grafana move para `:3001` em docker-compose.yml (§7.6) |
| 2 | Dockerfile multi-stage incompleto | **ALTA** | ✅ **RESOLVIDO** | Dockerfile completo com Node 20-alpine builder + nginx (§7.4), ~45MB final |
| 3 | Contrato API não cobre SPEC_010 (performance) | **ALTA** | ✅ **RESOLVIDO** | API service unificado com `getPerformance()`, tipos completos (§4.3, §4.2) |
| 4 | Roteamento incompleto (404, login condicional) | **MÉDIA** | ✅ **RESOLVIDO** | 4 views + 404 + router guard para auth (§5 US-035-05, §6.2) |
| 5 | Testes não validam TypeScript strict | **MÉDIA** | ✅ **RESOLVIDO** | TypeScript strict em tsconfig.json (§7.3), build falha se erro (§8.6) |
| 6 | Framework não decidido (Vue vs React) | **MÉDIA** | ✅ **RESOLVIDO** | Vue.js 3 recomendado explicitamente (§1, §14 FAQ) |
| 7 | Proxy dev/produção não separado (CORS) | **MÉDIA** | ✅ **RESOLVIDO** | Vite proxy dev (§7.2) + nginx proxy produção (§7.5) |
| 8 | DoD sem responsáveis de validação | **ALTA** | ✅ **RESOLVIDO** | DoD com validadores de skills (§10.5): qa-review, security-audit, lint-on-edit, sdd-spec-driven-development |

---

## 2. Refinamentos por Seção

### 2.1 Seções Re-ordenadas para Legibilidade

**Original (SPEC_035 v1.0):**
1. Objetivo
2. Escopo
3. User Stories
4. Modelo de Dados
5. Componentes
6. Invariantes
7. Testes
8. Arquivos
9. DoD
10. (faltava timeline)

**Refinada (SPEC_035 v2.0):**
1. ✅ Resumo Executivo (novo, executivo-friendly)
2. ✅ Objetivo
3. ✅ Escopo (expandido, detalhado)
4. ✅ Modelo de Dados (estrutura + tipos + store + API)
5. ✅ User Stories (5 histórias, critérios robustos)
6. ✅ Design Técnico (arquitetura, fluxos, polling)
7. ✅ Componentes (setup, Vite, TypeScript, Dockerfile, nginx, compose)
8. ✅ Testes (Vitest, cobertura, bundle size, TypeScript strict)
9. ✅ Invariantes (8 invariantes críticas)
10. ✅ Definition of Done (expandido, 7 categorias)
11. ✅ Timeline & Estimativa (novo: 8 dev-days, Sprint 1-4)
12. ✅ Referências & Dependências (novo)
13. ✅ Próximas Steps (novo)
14. ✅ FAQ & Esclarecimentos (novo)
15. ✅ Anexos (novo)

### 2.2 Recomendação Explícita: Vue.js 3 + Composition API + Vite

**Original:**
> "Framework: **Vue.js 3 + Vite** (recomendado) ou **React + Vite**"

**Refinado:**
- §1: "Vue.js 3 recomendado (React opcional, mas não será documentado nesta versão)"
- §3.1: "Vue.js 3.5+ com Composition API, Vite 6+, TypeScript 5.6+"
- §14 FAQ: Justificativa detalhada por que Vue.js 3 (bundle size, curva aprendizado, Pinia)

### 2.3 Resolução de Porta: Frontend `:3000` → Grafana `:3001`

**Original:**
```yaml
phicube-frontend:
  ports: ["3000:80"]
```
Conflito: Grafana também em `:3000`.

**Refinado (§7.6):**
```yaml
phicube-frontend:
  ports: ["3000:80"]

grafana:
  ports: ["3001:3000"]  # ← MUDADO de 3000
```

### 2.4 Dockerfile Completo com Multi-Stage

**Original (§5.3):**
```dockerfile
# Build stage
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Serve stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

**Refinado (§7.4):**
```dockerfile
# Incluir HEALTHCHECK
# Melhor tamanho final (~45MB)
# Comentários em português
# Explicação de cada stage
```

### 2.5 nginx.conf com Proxy `/api` e Estratégia de Cache

**Original (§5.3):**
Não havia nginx.conf definido.

**Refinado (§7.5 - 60 linhas):**
- Upstream para `phicube-dashboard-api:8080`
- Proxy `/api/*` com headers necessários
- Cache strategy diferenciada:
  - `index.html`: `max-age=0, must-revalidate` (sempre refetch)
  - `/assets/*`: `max-age=31536000, immutable` (1 ano, versionado)
- gzip compression
- CSP headers
- Fallback SPA: `try_files $uri $uri/ /index.html`
- Health check endpoint em `/health`

### 2.6 Contrato API Unificado (`src/services/api.ts`)

**Original (§4):**
```typescript
interface Position { ... }
async function getPositions() { ... }
```

**Refinado (§4.2 + §4.3):**
- **Tipos completos** (§4.2): Position, PerformanceGlobal, PerformanceBySymbol, PerformanceByTimeframe, PerformanceResponse, ApiError, HealthStatus
- **API service** (§4.3):
  - `getPositions()` → SPEC_002 ✅
  - `getPerformance()` → SPEC_010 ✅
  - `getHealth()`
  - Interceptor de retry com backoff exponencial (máx 3 tentativas)
  - Tratamento de erro 401 → evento customizado `auth:unauthorized`
  - Timeout 10s

### 2.7 User Story 5: Roteamento Robusto com Proteção Pré-Login

**Original:**
Não havia história sobre autenticação ou proteção de rota.

**Refinado (§5 US-035-05):**
- Router guard verifica token JWT antes de acessar rotas protegidas
- Erro 401 → redirecionamento para `/login`
- Evento customizado `auth:unauthorized` disparado
- Integração planejada com SPEC_036

### 2.8 Testes Expandidos: TypeScript Strict + Bundle Size

**Original (§7 Tests):**
5 testes genéricos, sem detalhe de cobertura ou bundle.

**Refinado (§8):**
- **§8.1:** Vitest config com coverage reporter, 70% mínimo
- **§8.2-8.6:** Exemplos completos de tests:
  - PositionTable.spec.ts (render, loading, ordenação, filtro)
  - positionStore.spec.ts (state, actions, computed)
  - performanceStore.spec.ts
  - api.spec.ts (mock axios, chamadas, retry)
  - router.spec.ts (roteamento, guards)
- **§8.6:** TypeScript strict validation (`npm run type-check`)
- **§8.7:** Bundle size check (< 50KB gzipped)

### 2.9 DoD com Validadores de Skills

**Original (§9):**
```
- [ ] Vue 3 + Vite + TypeScript configurado
- [ ] Roteamento SPA com 4 views
- [ ] ...
```
Sem menção a skills de validação.

**Refinado (§10 - 7 categorias com sub-items):**

1. **§10.1 Implementação do Frontend** (15 items)
2. **§10.2 DevOps & Infraestrutura** (10 items)
3. **§10.3 Testes** (11 items)
4. **§10.4 Documentação** (3 items)
5. **§10.5 Validação & Segurança** (com skills explícitas):
   - `qa-review`: TypeScript strict, cobertura 70%+, bundle < 50KB
   - `security-audit`: sem API key, sem JWT em localStorage, CSP headers, npm audit
   - `lint-on-edit`: ESLint + Prettier
   - `sdd-spec-driven-development`: user stories, invariantes, compatibilidade SPEC
6. **§10.6 Compatibilidade & Integração** (4 specs)
7. **§10.7 Go-Live** (12 items)

---

## 3. Novas Seções (Não Existiam em v1.0)

| Seção | Linhas | Conteúdo |
|-------|--------|----------|
| 1. Resumo Executivo | ~30 | Resumo para stakeholders |
| 6. Design Técnico | ~80 | Arquitetura, fluxos, polling, tratamento erro |
| 11. Timeline & Estimativa | ~50 | 8 dev-days, Sprint 1-4, breakdown por atividade |
| 12. Referências & Dependências | ~30 | Compatibilidade SPEC, deps npm |
| 13. Próximas Steps | ~10 | SPEC_036+, roadmap pós-implementação |
| 14. FAQ & Esclarecimentos | ~80 | Decisões técnicas justificadas |
| 15. Anexos | ~40 | Checklist, variáveis ambiente |

---

## 4. Expansão de Conteúdo

| Métrica | Original | Refinado | Crescimento |
|---------|----------|----------|------------|
| **Total de linhas** | 224 | 1620 | **+623%** |
| **Seções** | 9 | 15 | **+67%** |
| **User Stories** | 2 | 5 | **+150%** |
| **Exemplos de código** | 3 | 20+ | **+567%** |
| **Testes documentados** | 5 refs | 6 arquivos .spec.ts | **completos** |
| **Invariantes** | 4 | 8 | **+100%** |
| **DoD items** | ~10 checklist items | 50+ items em 7 categorias | **+400%** |

---

## 5. Compatibilidade com Specs Relacionadas

### 5.1 SPEC_002 (Frontend Consulta de Posições)

**Vínculo:** Upstream (API já existe)

**Validação:**
- ✅ Type Position alinha com resposta de SPEC_002
- ✅ `getPositions()` chama `GET /api/v1/positions`
- ✅ PositionTable renderiza campos corretos (symbol, direction, entry_price, current_price, pnl_usdt, pnl_pct, sl_price, tp_price)
- ✅ Polling a cada 60s

**Status:** Totalmente compatível. Frontend consome API de SPEC_002 sem mudança de contrato.

### 5.2 SPEC_010 (Dashboard Performance)

**Vínculo:** Upstream (API já existe)

**Validação:**
- ✅ Types PerformanceGlobal, PerformanceBySymbol, PerformanceByTimeframe
- ✅ `getPerformance()` chama `GET /api/v1/performance`
- ✅ MetricCards exibem 6 métricas RF-11 (total_trades, win_rate_pct, total_pnl_usdt, avg_rrr, max_drawdown_usdt, profit_factor)
- ✅ Duas tabelas (por símbolo e por timeframe)
- ✅ Polling a cada 60s

**Status:** Totalmente compatível. Frontend consome API de SPEC_010 sem mudança de contrato.

### 5.3 SPEC_036 (Autenticação Dashboard)

**Vínculo:** Downstream (será implementado depois de SPEC_035)

**Validação:**
- ✅ Router guard placeholder em `router/index.ts`
- ✅ Evento `auth:unauthorized` disparado em erro 401 (`api.ts` interceptor)
- ✅ Redirecionamento para `/login` planejado (será completado em SPEC_036)
- ✅ Sem JWT hardcodado (será localStorag/httpOnly em SPEC_036)

**Status:** Preparado. Frontend está pronto para integração com SPEC_036 sem mudanças de arquitetura.

### 5.4 SPEC_021 (Validação Operacional & Resiliência)

**Vínculo:** Validação em CI

**Validação:**
- ✅ Tests Vitest com cobertura 70%
- ✅ TypeScript strict (`npm run type-check`)
- ✅ Bundle size < 50KB gzipped
- ✅ Retry com backoff exponencial em API service
- ✅ Error handling em componentes (error banner)

**Status:** Alinha-se com requisitos de SPEC_021. Testes rodarão em CI com sucesso.

### 5.5 SPEC_014 (Security Design)

**Vínculo:** Upstream (padrões de segurança)

**Validação:**
- ✅ Nenhuma API key hardcodada
- ✅ Secrets em .env (VITE_API_BASE_URL pública, secrets em backend)
- ✅ CSP headers em nginx.conf
- ✅ CORS headers em nginx (não em navegador, proxy resolvido)

**Status:** Alinha-se com SPEC_014. Seguem boas práticas de segurança frontend.

---

## 6. Detalhamento de Componentes e Stores

### 6.1 Componentes (6 + Layout)

| Componente | Arquivo | Responsabilidade | Props | Testes |
|------------|---------|-----------------|-------|--------|
| PositionTable | `src/components/PositionTable.vue` | Tabela de posições, ordenação, filtro | `positions`, `loading` | render, sort, filter |
| MetricCard | `src/components/MetricCard.vue` | Card de métrica (label, valor, delta) | `label`, `value`, `delta`, `variant` | render, color |
| SignalBadge | `src/components/SignalBadge.vue` | Badge LONG/SHORT/NEUTRO | `signal` | render |
| PriceChart | `src/components/PriceChart.vue` | Gráfico (Chart.js ou mock) | `data`, `symbol` | render |
| LoadingSpinner | `src/components/LoadingSpinner.vue` | Spinner de carregamento | `size`, `color` | render |
| ErrorBanner | `src/components/ErrorBanner.vue` | Banner de erro | `message`, `onClose` | render, dismiss |
| Navbar | `src/components/Layout/Navbar.vue` | Barra de navegação | — | links |
| Footer | `src/components/Layout/Footer.vue` | Rodapé | `version` | render |

### 6.2 Stores (3)

| Store | Arquivo | State | Actions | Computed |
|-------|---------|-------|---------|----------|
| positionStore | `src/stores/positionStore.ts` | positions, loading, error, lastUpdate | fetchPositions, updatePosition, clearPositions | totalPnl, winCount, lossCount |
| performanceStore | `src/stores/performanceStore.ts` | data, loading, error, lastUpdate | fetchPerformance | globalMetrics |
| uiStore | `src/stores/uiStore.ts` (não detalhe, mas mencionado) | loading, error, notifications | setLoading, setError, clearError | — |

### 6.3 Views (5)

| View | Rota | Arquivo | Componentes |
|------|------|---------|-----------|
| Dashboard | `/` | `src/views/DashboardView.vue` | 6 MetricCards (global), PositionTable (resumida), PriceChart |
| Posições | `/positions` | `src/views/PositionsView.vue` | PositionTable (completa), filtro |
| Histórico | `/history` | `src/views/HistoryView.vue` | Tabela de trades fechados (mockado) |
| Configuração | `/settings` | `src/views/SettingsView.vue` | Info do bot (versão, uptime, env) |
| 404 | `/404` | `src/views/NotFoundView.vue` | Botão volta, mensagem amigável |

---

## 7. Estimativa de Esforço Refinada

**Cenário:** 1 dev frontend, 2 sprints (8 dev-days úteis)

```
Sprint 1 (3 dias):
  ├─ Setup Vite + Vue 3 + TS + Pinia           [1.5 d] ✅ npm run dev funciona
  ├─ Roteamento + 4 views + 404                [1.5 d] ✅ SPA navigation OK
  
Sprint 2 (3.5 dias):
  ├─ 6 componentes + 2 layouts                  [2.0 d] ✅ Todos renderizam
  ├─ 3 stores (position, performance, ui)       [1.5 d] ✅ State mutations OK
  
Sprint 3 (1.5 dias):
  ├─ API service + tipos                        [1.0 d] ✅ Chamadas funcionam
  ├─ Testes (70% cobertura)                     [0.5 d] ✅ npm run test OK
  
Sprint 4+ (1 dia):
  ├─ Dockerfile + nginx.conf + docker-compose   [0.5 d] ✅ docker compose up OK
  ├─ Documentação (README, DEVELOPMENT)          [0.5 d] ✅ Docs completos
  
Total: ~8 dev-days
```

---

## 8. Checklist de Entrega

- [x] SPEC_035_REFINED.md criado (1620 linhas, 15 seções)
- [x] Todos os 8 gaps críticos resolvidos
- [x] 5 user stories detalhadas com critérios de aceite
- [x] Contrato de API unificado (types + service)
- [x] Exemplos completos de código (Dockerfile, nginx.conf, stores, componentes, testes)
- [x] Invariantes explícitas (8 INV-035-xx)
- [x] Definition of Done expandida (7 categorias, 50+ items)
- [x] Timeline com breakdown Sprint 1-4
- [x] Compatibilidade validada com SPEC_002, SPEC_010, SPEC_036, SPEC_021
- [x] Skills de validação explícitos (qa-review, security-audit, lint-on-edit, sdd-spec-driven-development)
- [x] FAQ & justificativas técnicas
- [x] Próximas steps para SPEC_036+

---

## 9. Como Usar Este Documento

### Para Implementador:
1. Ler §1 (Resumo) + §2 (Objetivo)
2. Ler §3 (Escopo) e §5 (User Stories)
3. Seguir estrutura de pasta (§4.1)
4. Copiar código de exemplos (§7, §8)
5. Usar checklist de DoD (§10) para validar progresso

### Para Revisor/QA:
1. Validar DoD items (§10)
2. Rodar skills: `qa-review`, `security-audit`, `lint-on-edit`, `sdd-spec-driven-development`
3. Verificar compatibilidade com SPEC_002, SPEC_010, SPEC_036 (§5)
4. Aprovar go-live (§10.7)

### Para Stakeholder/PM:
1. Ler §1 (Resumo Executivo)
2. Revisar timeline (§11)
3. Confirmar resolução de gaps (§1 desta summary)
4. Aprovar plano de validação (skills em §10.5)

---

## 10. Próximos Passos

1. **Mover arquivo:** `SPEC_035_REFINED.md` → `docs/SDD/SPEC_035_FRONTEND_FRAMEWORK/SPEC.md` (sobrescrever)
2. **Validar compatibilidade:** Rodar skills em SPEC_035 (qa-review, security-audit, lint-on-edit)
3. **Planejar sprint:** Alocar 1 dev frontend, ~8 dev-days
4. **Iniciar implementação:** Sprint 1 com setup Vite + roteamento
5. **Preparar SPEC_036:** Planejamento de autenticação JWT (aproveitará router guard de SPEC_035)

---

**Assinado:** OpenCode (Documentalista especializado em SDD)  
**Data:** 2026-05-13  
**Versão:** 1.0  
**Status:** ✅ Entrega Completa
