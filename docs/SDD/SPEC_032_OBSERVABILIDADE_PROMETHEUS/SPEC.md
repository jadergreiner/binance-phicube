# SPEC_032 — Observabilidade com Prometheus

**ID:** SPEC_032
**Título:** Observabilidade com Prometheus + Grafana
**Data:** 2026-05-10
**Status:** Rascunho
**Versão:** 1.0
**Dependências:** SPEC_007 (resiliência), SPEC_017 (healthcheck)
**PRD §:** Fase 2 — "Monitoramento e métricas"

---

## 1. Objetivo

Exportar métricas do bot e da dashboard API no formato Prometheus, permitindo coleta, alerta e visualização histórica com Grafana. Métricas cobrem: trades executados, sinais gerados, healthcheck do bot, latência da exchange e erros.

---

## 2. Escopo

### Dentro do escopo
- Endpoint `GET /metrics` no formato Prometheus (porta 8000 no bot, 8080 na API)
- Métricas: trades (total, win, loss), sinais (buy/sell por símbolo), heartbeat, erros
- Contadores, histogramas e gauges via `prometheus_client`
- Integração com docker-compose: container Prometheus + Grafana
- Painel Grafana básico exportado como JSON (`monitoring/grafana_dashboard.json`)
- Alerta de ausência de heartbeat por >5min

### Fora do escopo
- Métricas de negócio avançadas (Sharpe, Sortino)
- Tracing distribuído (OpenTelemetry)
- Alerta via Telegram integrado ao AlertManager

---

## 3. User Stories

### US-032-01 — Métricas de trading expostas
**Como** operador,
**quero** acessar `http://bot:8000/metrics` e ver trades, sinais, PnL,
**para** monitorar a saúde do bot em tempo real.

**Critério de aceite:**
- Endpoint responde 200 no formato text/plain Prometheus
- Métricas incluem: `phicube_trades_total{status="win|loss"}`, `phicube_signals_total{direction="buy|sell"}`

### US-032-02 — Painel Grafana operacional
**Como** operador,
**quero** um painel Grafana pré-configurado com visão geral do bot,
**para** não precisar criar do zero.

**Critério de aceite:**
- Painel importável via `monitoring/grafana_dashboard.json`
- Mostra: trades por hora, win rate, sinais por símbolo, heartbeat (timeline)

---

## 4. Modelo de Dados

### Métricas Prometheus

| Métrica | Tipo | Labels | Descrição |
|---------|------|--------|-----------|
| `phicube_trades_total` | Counter | `symbol`, `direction`, `status` | Trades executados |
| `phicube_signals_total` | Counter | `symbol`, `timeframe`, `direction` | Sinais gerados |
| `phicube_heartbeat_seconds` | Gauge | — | Timestamp do último heartbeat |
| `phicube_errors_total` | Counter | `module`, `error_type` | Erros por módulo |
| `phicube_positions_open` | Gauge | — | Posições abertas atualmente |
| `phicube_candle_latency_seconds` | Histogram | `symbol` | Latência de busca de candles |
| `phicube_pnl_usdt_total` | Counter | `symbol` | PnL acumulado (não realizado + realizado) |

---

## 5. Componentes

### 5.1 `src/monitoring/metrics.py` — novo módulo

```python
from prometheus_client import Counter, Gauge, Histogram, generate_latest, REGISTRY

trades_total = Counter("phicube_trades_total", "Total de trades", ["symbol", "direction", "status"])
signals_total = Counter("phicube_signals_total", "Sinais gerados", ["symbol", "timeframe", "direction"])
heartbeat = Gauge("phicube_heartbeat_seconds", "Último heartbeat (unix timestamp)")
errors_total = Counter("phicube_errors_total", "Erros por módulo", ["module", "error_type"])
positions_open = Gauge("phicube_positions_open", "Posições abertas")
candle_latency = Histogram("phicube_candle_latency_seconds", "Latência fetch_ohlcv", ["symbol"])
pnl_total = Counter("phicube_pnl_usdt_total", "PnL acumulado USDT", ["symbol"])

def get_metrics() -> str:
    return generate_latest(REGISTRY).decode()
```

### 5.2 Endpoint no bot (`src/main.py`)

```python
# Adicionar ao aiohttp server ou route separada
async def metrics_handler(request):
    return web.Response(text=get_metrics(), content_type="text/plain; charset=utf-8")
```

### 5.3 Endpoint na Dashboard API (`src/api/main.py`)

```python
from src.monitoring.metrics import get_metrics

@router.get("/metrics")
async def metrics():
    return Response(content=get_metrics(), media_type="text/plain")
```

### 5.4 docker-compose — serviços

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    container_name: phicube-prometheus
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    container_name: phicube-grafana
    volumes:
      - ./monitoring/grafana_dashboard.json:/etc/grafana/provisioning/dashboards/dashboard.json
      - grafana-data:/var/lib/grafana
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
```

---

## 6. Invariantes

| ID | Invariante |
|----|-----------|
| INV-032-01 | `GET /metrics` nunca falha — se `prometheus_client` indisponível, retorna 500 |
| INV-032-02 | Métricas de heartbeat nunca resetam (Gauge, não Counter) |
| INV-032-03 | Rótulos de métricas são limitados (evitar alta cardinalidade) |

---

## 7. Testes

| ID | Descrição |
|----|-----------|
| TEST_032_01 | `GET /metrics` retorna 200 com formato Prometheus válido |
| TEST_032_02 | Counter `phicube_trades_total` incrementa após trade simulado |
| TEST_032_03 | `phicube_heartbeat_seconds` atualiza no tick do bot |
| TEST_032_04 | `phicube_errors_total` registra erro simulado |
| TEST_032_05 | Histograma `phicube_candle_latency` registra observação |

---

## 8. Arquivos

| Arquivo | Mudança |
|---------|---------|
| `src/monitoring/metrics.py` | Criado — métricas Prometheus |
| `src/main.py` | Modificado — endpoint `/metrics` |
| `src/api/main.py` | Modificado — endpoint `/metrics` |
| `monitoring/prometheus.yml` | Criado — config scrape |
| `monitoring/grafana_dashboard.json` | Criado — painel pré-configurado |
| `docker-compose.yml` | Modificado — serviços prometheus + grafana |
| `tests/monitoring/test_metrics.py` | Criado — TEST_032_01 a 05 |

---

## 9. Definition of Done

- [ ] Endpoint `/metrics` funcional no bot e na API
- [ ] Contadores, gauges e histogramas registrando dados reais
- [ ] Prometheus coletando métricas do bot e API
- [ ] Grafana com painel importável mostrando trades, sinais, heartbeat
- [ ] TEST_032_01 a 05 passando
- [ ] `ruff check src/ tests/` limpo
