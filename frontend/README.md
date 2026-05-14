# Phicube Frontend SPA

Frontend Single Page Application para o Binance Phicube Dashboard, construído com Vue.js 3 + TypeScript + Vite.

## Tecnologias

- **Framework:** Vue.js 3 (Composition API)
- **Linguagem:** TypeScript (strict mode)
- **Build:** Vite 6.x
- **Roteamento:** Vue Router 4 (lazy-loaded)
- **Estado:** Pinia 2.x
- **HTTP:** Axios 1.x com retry + backoff
- **Testes:** Vitest + @vue/test-utils + jsdom
- **Container:** Docker multi-stage (nginx:alpine)
- **Lint/Format:** ESLint + Prettier

## Quick Start

```bash
# Instalar dependências
npm install

# Servidor de desenvolvimento (porta 3000)
npm run dev

# Build de produção
npm run build

# Preview do build
npm run preview

# Testes
npm run test

# Testes com cobertura
npm run test:coverage

# TypeScript check
npm run type-check

# Lint
npm run lint

# Format
npm run format
```

## Variáveis de Ambiente

```env
VITE_API_BASE_URL=http://localhost:8080/api/v1
VITE_APP_ENV=development
```

## Estrutura do Projeto

```
frontend/
├── src/
│   ├── components/       # Componentes reutilizáveis
│   │   └── Layout/       # Componentes de layout (Navbar, Footer)
│   ├── views/            # Páginas/Views (Dashboard, Positions, etc.)
│   ├── stores/           # Pinia stores (posições, performance, UI)
│   ├── services/         # API service, types, config
│   ├── router/           # Vue Router config
│   ├── styles/           # CSS global (main.css, components.css)
│   ├── composables/      # Composables reutilizáveis
│   ├── App.vue           # Componente raiz
│   └── main.ts           # Ponto de entrada
├── tests/                # Configuração de testes
├── Dockerfile            # Docker multi-stage build
├── nginx.conf            # Configuração nginx
└── vite.config.ts        # Configuração Vite
```

## Docker

```bash
# Build da imagem
docker build -t phicube-frontend .

# Executar container
docker run -p 3000:80 phicube-frontend

# Via Docker Compose (raiz do projeto)
docker compose up -d
```

## Links

- [DEVELOPMENT.md](./DEVELOPMENT.md) — Guia de desenvolvimento
- [SPEC_035.md](../docs/SDD/SPEC_035_FRONTEND_FRAMEWORK/SPEC.md) — Especificação técnica
- [PRD.md](../PRD.md) — Product Requirement Document
