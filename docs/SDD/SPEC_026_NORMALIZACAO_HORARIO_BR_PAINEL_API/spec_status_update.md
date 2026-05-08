# SPEC_026 — Status Update

- **Data:** 2026-05-08
- **Estado:** Concluída
- **Resumo:** APIs do painel passaram a expor horário brasileiro (`*_br`) com metadado de timezone, mantendo campos UTC legados para compatibilidade.

## Progresso

- [x] Utilitário único de serialização temporal criado
- [x] Rotas do painel normalizadas com `*_br` e `timezone`
- [x] Frontend priorizando `*_br` com fallback legado
- [x] Testes de contrato e documentação SDD atualizados

## Evidências

- `src/api/datetime_utils.py`
- `src/api/routes/positions.py`
- `src/api/routes/signals.py`
- `src/api/routes/trades.py`
- `src/api/routes/health.py`
- `src/api/routes/performance.py`
- `src/frontend/static/app.js`
- `tests/api/test_signal_history.py`
- `tests/api/test_trade_history.py`
- `tests/api/test_health_bot_process.py`
- `tests/api/test_health_route_namespace.py`
- `tests/api/test_bot_activity.py`
- `tests/api/test_performance_endpoints.py`
- `tests/api/test_performance_by_group.py`
- `tests/dashboard/test_api.py`
- `tests/dashboard/test_frontend.py`
