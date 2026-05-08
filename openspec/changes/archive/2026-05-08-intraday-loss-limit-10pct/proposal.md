## Why

O sistema ainda permite novas entradas mesmo após perda relevante no pregão, aumentando risco de efeito cascata em dias de alta volatilidade. Bloquear novas entradas após 10% de perda intraday reduz drawdown extremo e melhora disciplina operacional.

## What Changes

- Adicionar guarda de perda intraday com limiar fixo de 10% sobre capital de referência diário.
- Bloquear novas entradas quando o limite for atingido, preservando gestão de posições já abertas.
- Registrar motivo de bloqueio em logs/eventos para rastreabilidade operacional.
- Reiniciar elegibilidade de novas entradas na virada do dia operacional.

## Capabilities

### New Capabilities
- `intraday-loss-guard`: bloqueia novas entradas após perda acumulada intraday atingir 10%.

### Modified Capabilities
- Nenhuma.

## Impact

- Código: `src/trading/risk_manager.py`, possível integração em `src/trading/trading_monitor.py`.
- Testes: `tests/trading/test_risk_manager.py` e testes de fluxo de monitoramento.
- Operação: evita abertura de novas posições em regime de perda diária excessiva.
