# Tasks - SPEC_032_OBSERVABILIDADE_PROMETHEUS

## Active

## Waiting On

## Someday

- [ ] **Criar dashboard Grafana JSON automatizado** - importar automaticamente no provisioning
  - Atualmente o provider está configurado mas não tem JSON de dashboard
  - Path: `monitoring/grafana/dashboards/`

- [ ] **Instrumentar métricas adicionais** - expandir cobertura da SPEC_032
  - `api_requests_total`: chamadas à API Binance (pontos 3 e 8)
  - `pnl_realized_win_total` / `pnl_realized_loss_total`: PnL realizado ao fechar trades
  - `errors_total`: erros capturados por módulo
  - `candle_latency_seconds`: latência de `fetch_ohlcv()`

## Done

- [x] ~~Configuração básica~~ (2026-05-12)
  - `pyproject.toml`: dependência `prometheus-client>=0.19.0`
  - `src/config/settings.py`: env vars `prometheus_enabled`, `prometheus_port`, `prometheus_bind_host`

- [x] ~~Módulo de métricas~~ (2026-05-12)
  - `src/monitoring/metrics.py`: 18 métricas (Info, Gauge, Counter, Histogram)
  - Funções de conveniência para todos pontos de instrumentação
  - Wrappers seguros que não lançam exceção

- [x] ~~Testes~~ (2026-05-12)
  - `tests/monitoring/test_metrics.py`: 17 testes
  - Todos passando ✅

- [x] ~~Integrar no bot~~ (2026-05-12)
  - `src/main.py`: `metrics.initialize()` + `metrics.start_metrics_server()`
  - Instrumentação TradingMonitor: heartbeat, tick_duration, positions_open, signal_rejected

- [x] ~~Instrumentar componentes~~ (2026-05-12)
  - `src/strategy/signal_engine.py`: `record_signal_evaluated()`, `record_signal_detected()`
  - `src/trading/order_manager.py`: `record_trade_executed()`

- [x] ~~Rota /metrics na API~~ (2026-05-12)
  - `src/api/main.py`: endpoint `/metrics` retornando `get_metrics()`

- [x] ~~Configs monitoring/~~ (2026-05-12)
  - `monitoring/prometheus.yml`: scrape configs para bot e API
  - `monitoring/grafana/datasources/prometheus.yml`: datasource provisioning
  - `monitoring/grafana/dashboards/dashboard.yml`: dashboard provider

- [x] ~~docker-compose.yml~~ (2026-05-12)
  - Serviço `prometheus`: `prom/prometheus:v2.49.1` na porta 9090
  - Serviço `grafana`: `grafana/grafana:10.4.0` na porta 3000
  - Volumes `prometheus_data` e `grafana_data`
  - `phicube` com `expose: "8000"`

- [x] ~~Commit e Push~~ (2026-05-12)
  - Commit: `feat(monitoring): add Prometheus observability (SPEC_032)`
  - Hash: `4f43020`
  - 13 arquivos alterados (1442 inserções, 124 deleções)
