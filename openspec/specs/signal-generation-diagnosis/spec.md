# signal-generation-diagnosis Specification

## Purpose
TBD - created by archiving change analise-de-sinais-gerados. Update Purpose after archive.
## Requirements
### Requirement: Diagnostico deterministico do pipeline de sinal
O sistema SHALL classificar cada ciclo de avaliacao de sinal por `symbol` e `timeframe` em um resultado diagnostico deterministico, cobrindo as etapas `engine`, `risk`, `order` e `persist`.

#### Scenario: Classificacao de ciclo sem setup
- **WHEN** o `SignalEngine` nao gerar direcao valida para a candle fechada
- **THEN** o sistema MUST registrar o ciclo como `NO_SETUP_DETECTED` com `symbol`, `timeframe` e `candle_close_time`

#### Scenario: Classificacao de rejeicao por risco
- **WHEN** houver sinal do `SignalEngine` e o `RiskManager` rejeitar por quantidade zero apos arredondamento
- **THEN** o sistema MUST registrar o ciclo como `REJECTED_BY_RISK` com razao `quantity_zero_after_rounding`

### Requirement: Evidencia numerica minima para rejeicao de quantidade
O sistema MUST registrar valores numericos minimos de diagnostico para cenarios de risco rejeitado por quantidade, incluindo `qty_raw` e `qty_rounded`.

#### Scenario: Registro de rounding para auditoria
- **WHEN** a decisao final do ciclo for rejeicao por risco de quantidade
- **THEN** o sistema SHALL persistir `qty_raw`, `qty_rounded`, `risk_reason` e `final_status` em trilha de auditoria consultavel

### Requirement: Deteccao de interrupcao de pipeline
O sistema MUST identificar ausencia prolongada de sinais novos e diferenciar entre ausencia legitima de setup e interrupcao tecnica do pipeline.

#### Scenario: Pipeline interrompido por falha tecnica
- **WHEN** houver novos candles fechados no periodo monitorado sem emissao de evento diagnostico por ciclo
- **THEN** o sistema SHALL classificar o estado como `PIPELINE_INTERRUPTED`

#### Scenario: Lacuna de persistencia
- **WHEN** houver evidencia de decisao de sinal em logs/execucao sem registro correspondente em persistencia
- **THEN** o sistema SHALL classificar o estado como `PERSISTENCE_GAP`

