# SPEC_025 — Status Update

- **Data:** 2026-05-08
- **Estado:** Concluída
- **Resumo:** Seção de sinais adicionada ao dashboard e diagnóstico estruturado de não execução persistido por sinal.

## Progresso

- [x] Endpoint `GET /signals/history` implementado
- [x] Persistência de desfecho por sinal implementada
- [x] Frontend com tabela “Sinais Gerados” implementado
- [x] Testes de API, repository, risco/monitor e frontend adicionados

## Evidências

- `tests/api/test_signal_history.py`
- `tests/trading/test_risk_manager.py`
- `tests/trading/test_trading_monitor_signal_outcomes.py`
- `tests/dashboard/test_frontend.py`
