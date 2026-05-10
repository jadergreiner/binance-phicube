# ─── Estágio de build ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Instala dependências de compilação
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir build && \
    pip install --no-cache-dir \
        ccxt \
        pandas \
        numpy \
        motor \
        pymongo \
        pydantic \
        pydantic-settings \
        python-dotenv \
        structlog \
        aiohttp \
        asyncio-throttle

# ─── Estágio de execução ──────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Usuário não-root para segurança
RUN useradd --create-home --shell /bin/bash phicube
WORKDIR /app

# Copia pacotes instalados do builder
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin

# Copia código-fonte
COPY src/ ./src/

USER phicube

# Healthcheck — verifica se o processo está vivo
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import src.config.settings" || exit 1

CMD ["python", "-m", "src.main"]
