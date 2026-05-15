# Tasks

## Done

- [x] Criar módulo compartilhado de métricas em `src/common/metrics.py`
- [x] Unificar cálculo de `total_trades`, `win_rate_pct`, `total_pnl_usdt`, `avg_rrr`, `max_drawdown_usdt` e `profit_factor`
- [x] Preservar semântica: `profit_factor = 0.0` quando `gross_loss == 0`
- [x] Preservar convenção: `max_drawdown_usdt` não-positivo
- [x] Refatorar `src/storage/repository.py` para usar o núcleo compartilhado
- [x] Preservar ordenação por `closed_at` no caminho de repository
- [x] Refatorar `src/backtest/engine.py::_calc_metrics` para usar o núcleo compartilhado
- [x] Refatorar `src/backtest/engine.py::_build_result` para reutilizar o núcleo com `pnl_field`
- [x] Adicionar testes unitários do núcleo em `tests/common/test_metrics.py`
- [x] Validar regressão em testes de storage e backtest
