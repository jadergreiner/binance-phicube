## Why

Os cálculos de métricas de performance estão duplicados e semanticamente divergentes entre produção (`MongoRepository`) e backtest (`BacktestEngine`). Isso aumenta risco de regressão, dificulta auditoria e gera inconsistência em relatórios para o mesmo conjunto de trades.

## What Changes

- Introduzir um núcleo único de cálculo de métricas orientado a dados numéricos (PnL e RRR), reutilizável por produção e backtest.
- Consolidar os fluxos de métricas de `MongoRepository._calc_metrics`, `BacktestEngine._calc_metrics` e da etapa de métricas em `BacktestEngine._build_result`.
- Preservar semântica operacional existente:
  - `profit_factor = 0.0` quando não há perdas (`gross_loss == 0`);
  - `max_drawdown_usdt` não-positivo (0 ou negativo).
- Definir contrato explícito de normalização e arredondamento para evitar drift entre consumidores.

## Capabilities

### New Capabilities
- `performance-metrics-unification`: cálculo centralizado e consistente de métricas de performance para produção e backtest.

### Modified Capabilities
- Nenhuma.

## Impact

- Código afetado:
  - `src/storage/repository.py`
  - `src/backtest/engine.py`
  - novo módulo compartilhado em `src/common/`
- Testes afetados:
  - `tests/storage/test_performance_metrics.py`
  - `tests/backtest/test_engine.py`
  - novos testes unitários para o núcleo de métricas
- Risco principal: regressão silenciosa em fórmulas e sinais (drawdown/profit factor) ao consolidar fluxos.
