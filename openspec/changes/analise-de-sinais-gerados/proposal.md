## Why

Foi observado que o último sinal processado ocorreu em **13/05/2026 11:31:05** para `PLTRUSDT` (`15m`, `SHORT`) com status `REJECTED_RISK_QTY_ZERO` e razão `quantity_zero_after_rounding`, sem novos sinais subsequentes. Precisamos investigar a causa-raiz para entender se houve bloqueio legítimo por risco/configuração ou regressão no pipeline de geração e persistência de sinais.

## What Changes

- Mapear o fluxo completo desde a avaliação de sinal até persistência/auditoria para identificar onde a geração de novos sinais está interrompida.
- Auditar regras de risco e arredondamento de quantidade (`quantity_zero_after_rounding`) para confirmar se o bloqueio é esperado para `PLTRUSDT` no contexto atual.
- Validar ingestão de candles e gatilhos do loop de monitoramento para descartar travamento, drift de horário ou falha silenciosa.
- Definir critérios objetivos de diagnóstico e evidências mínimas (logs, métricas e registros em Mongo) para concluir a investigação.
- Propor correção ou ajuste operacional caso seja identificado comportamento indevido.

## Capabilities

### New Capabilities
- `signal-generation-diagnosis`: Capacidade de diagnosticar de forma determinística interrupções na geração de sinais, cobrindo decisão do `SignalEngine`, gate de risco, arredondamento de quantidade e persistência.

### Modified Capabilities
- `runtime-observability`: Ajustes de rastreabilidade para facilitar identificação de cenários com ausência prolongada de sinais.

## Impact

- Código potencialmente afetado: `src/main.py`, `src/trading/risk_manager.py`, `src/trading/order_manager.py`, `src/strategy/signal_engine.py`, `src/storage/repository.py` e testes relacionados.
- APIs: sem mudança funcional externa esperada nesta etapa de investigação.
- Dependências/sistemas: possível impacto em logs estruturados, métricas operacionais e consultas diagnósticas em MongoDB.
