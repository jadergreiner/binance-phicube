# SPEC_035 — Modernização do Frontend

**ID:** SPEC_035
**Título:** Modernização do Frontend com Framework SPA
**Data:** 2026-05-10
**Status:** Rascunho
**Versão:** 1.0
**Dependências:** SPEC_002 (frontend consulta), SPEC_010 (dashboard performance)
**PRD §:** Fase 2 — "Interface de usuário"

---

## 1. Objetivo

Substituir o frontend vanilla HTML/CSS/JS atual (páginas estáticas servidas pelo FastAPI) por uma **Single Page Application (SPA)** com framework moderno, proporcionando melhor experiência de usuário, manutenibilidade e reatividade.

O frontend vanilla atual atende funcionalmente mas é difícil de manter, não tem roteamento, estado global ou componentes reutilizáveis.

---

## 2. Escopo

### Dentro do escopo
- Framework: **Vue.js 3 + Vite** (recomendado) ou **React + Vite**
- SPA com roteamento: dashboard, posições, histórico, configuração
- Consumo da API existente (`/api/v1/*`) via fetch/axios
- Componentes reutilizáveis: tabela de posições, cartão de métrica, gráfico
- Proxy dev (`vite.config.ts`) para API em `localhost:8080`
- Dockerfile separado para build + nginx serving
- Substituição progressiva: novo frontend coexiste com o antigo em `/app/`

### Fora do escopo
- Testes end-to-end (Cypress/Playwright)
- PWA (offline support)
- i18n (multi-idioma)
- Tema customizável (dark/light)

---

## 3. User Stories

### US-035-01 — Roteamento SPA
**Como** operador,
**quero** navegar entre dashboards sem recarregar a página,
**para** ter uma experiência mais fluida.

**Critério de aceite:**
- `/` → Dashboard principal
- `/positions` → Posições abertas
- `/history` → Histórico de trades
- `/settings` → Configuração

### US-035-02 — Componentização
**Como** desenvolvedor,
**quero** ter componentes reutilizáveis (DataTable, MetricCard, PriceChart),
**para** adicionar novas telas rapidamente.

**Critério de aceite:**
- `PositionTable.vue` — tabela com colunas configurável, ordenação, filtro
- `MetricCard.vue` — cartão com label, valor, variação (verde/vermelho)
- `SignalBadge.vue` — badge de sinal (LONG verde, SHORT vermelho, NEUTRO cinza)

---

## 4. Modelo de Dados

### Estrutura do projeto frontend

```
frontend/
  src/
    components/
      PositionTable.vue
      MetricCard.vue
      SignalBadge.vue
      PriceChart.vue
    views/
      DashboardView.vue
      PositionsView.vue
      HistoryView.vue
      SettingsView.vue
    services/
      api.ts              # Wrapper fetch para API
    router/
      index.ts            # Vue Router config
    App.vue
    main.ts
  package.json
  vite.config.ts
  Dockerfile
  tsconfig.json
```

### Contrato API (consumido)

```typescript
// src/services/api.ts
interface Position {
  symbol: string;
  direction: "LONG" | "SHORT";
  entry_price: number;
  current_price: number;
  pnl_usdt: number;
  sl_price: number;
  tp_price: number;
}

async function getPositions(): Promise<Position[]> {
  const res = await fetch("/api/v1/positions");
  return res.json();
}
```

---

## 5. Componentes

### 5.1 Setup Vite + Vue 3

```bash
npm create vite@latest frontend -- --template vue-ts
cd frontend
npm install vue-router@4
```

### 5.2 Proxy dev (`vite.config.ts`)

```typescript
export default defineConfig({
  server: {
    proxy: {
      "/api": "http://localhost:8080",
      "/health": "http://localhost:8080",
    },
  },
});
```

### 5.3 Dockerfile multi-stage

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

### 5.4 docker-compose — serviço frontend

```yaml
services:
  phicube-frontend:
    build: ./frontend
    container_name: phicube-frontend
    ports:
      - "3000:80"
    depends_on:
      - phicube-dashboard-api
    restart: unless-stopped
```

---

## 6. Invariantes

| ID | Invariante |
|----|-----------|
| INV-035-01 | Frontend nunca faz chamada direta ao MongoDB |
| INV-035-02 | Toda requisição passa pelo proxy `/api` (evita CORS em produção) |
| INV-035-03 | Frontend não tem acesso a secrets (api_key, api_secret) |
| INV-035-04 | Build falha se TypeScript tem erro de tipo |

---

## 7. Testes

| ID | Descrição |
|----|-----------|
| TEST_035_01 | Build `npm run build` completo sem erros |
| TEST_035_02 | Proxy dev redireciona `/api` para `localhost:8080` |
| TEST_035_03 | Componente PositionTable renderiza dados mockados |
| TEST_035_04 | Roteamento navega entre views sem recarregar |
| TEST_035_05 | Dockerfile build produz imagem < 50MB |

---

## 8. Arquivos

| Arquivo | Mudança |
|---------|---------|
| `frontend/package.json` | Criado |
| `frontend/vite.config.ts` | Criado |
| `frontend/tsconfig.json` | Criado |
| `frontend/index.html` | Criado |
| `frontend/src/main.ts` | Criado |
| `frontend/src/App.vue` | Criado |
| `frontend/src/router/index.ts` | Criado |
| `frontend/src/services/api.ts` | Criado |
| `frontend/src/components/*.vue` | Criado (4 componentes) |
| `frontend/src/views/*.vue` | Criado (4 views) |
| `frontend/Dockerfile` | Criado |
| `frontend/nginx.conf` | Criado |
| `docker-compose.yml` | Modificado — serviço frontend |

---

## 9. Definition of Done

- [ ] Vue 3 + Vite + TypeScript configurado
- [ ] Roteamento SPA com 4 views
- [ ] Componentes PositionTable, MetricCard, SignalBadge, PriceChart
- [ ] API service consumindo `/api/v1/*`
- [ ] Dockerfile multi-stage build + nginx
- [ ] `docker compose up` serve frontend em `:3000`
- [ ] TEST_035_01 a 05 passando
