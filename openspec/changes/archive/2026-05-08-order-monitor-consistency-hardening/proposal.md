## Why

O monitor de ordens pode encerrar trades como `CLOSED_MANUAL` por inferência
frágil quando há divergência de formato de símbolo (`ATOMUSDT` vs
`ATOM/USDT:USDT`) ou indisponibilidade temporária de consultas de ordem.
Isso gera fechamentos muito curtos com PnL estimado quase zero, degradando a
qualidade operacional e a confiabilidade dos dados de histórico.

## What Changes

- Normalizar símbolos antes da comparação de posição aberta no `OrderMonitor`.
- Exigir confirmação de posição ausente em 2 ciclos consecutivos antes de executar fechamento manual.
- Tornar robusto o fallback após `OrderNotFound`, evitando encerramento prematuro sem confirmação adicional de estado da posição.
- Melhorar telemetria para distinguir "manual close confirmado" de "reconciliação inconclusiva".

## Capabilities

### New Capabilities

- `order-monitor-reconciliation`: regras de consistência para reconciliação de posições e fechamento manual seguro no monitor de ordens.

### Modified Capabilities

- Nenhuma.

## Impact

- Código: `src/monitoring/order_monitor.py`, possível utilitário de normalização em `src/exchange/binance_client.py` ou camada comum.
- Testes: `tests/monitoring/test_order_monitor.py` e cenários de reconciliação de posição.
- Operação: redução de `CLOSED_EXTERNAL` indevido e menor incidência de trades muito curtos por falsa detecção de fechamento.
