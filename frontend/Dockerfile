# ===== Stage 1: Builder =====
FROM node:20-alpine AS builder

WORKDIR /app

# Cache de dependências
COPY package*.json ./
RUN npm ci && npm cache clean --force

# Build da aplicação
COPY . .
RUN npm run build

# ===== Stage 2: Runtime (nginx) =====
FROM nginx:1.27-alpine

# Remove configuração padrão do nginx
RUN rm /etc/nginx/conf.d/default.conf

# Copia configuração customizada
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copia build do stage anterior
COPY --from=builder /app/dist /usr/share/nginx/html

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
