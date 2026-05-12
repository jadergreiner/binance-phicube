FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src/ ./src/
COPY tools/ ./tools/

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -e .

FROM python:3.11-slim AS runtime

RUN useradd --create-home --shell /bin/bash phicube
WORKDIR /app

# Install mongodump/mongorestore for automated MongoDB backup (SPEC_031)
# Uses --allow-unauthenticated because Debian 13 (Trixie) sqv rejects MongoDB's SHA1 key
RUN apt-get update && apt-get install -y --no-install-recommends \
    gnupg curl ca-certificates && \
    curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
    gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg && \
    echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg allow-insecure=yes ] http://repo.mongodb.org/apt/debian bookworm/mongodb-org/7.0 main" \
    > /etc/apt/sources.list.d/mongodb-org-7.0.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends --allow-unauthenticated mongodb-database-tools && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app/

RUN mkdir -p /app/logs && chown phicube:phicube /app/logs

USER phicube

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import src.config.settings" || exit 1

CMD ["python", "-m", "src.main"]
