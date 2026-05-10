FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src/ ./src/

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -e .

FROM python:3.11-slim AS runtime

RUN useradd --create-home --shell /bin/bash phicube
WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app/

RUN mkdir -p /app/logs && chown phicube:phicube /app/logs

USER phicube

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import src.config.settings" || exit 1

CMD ["python", "-m", "src.main"]
