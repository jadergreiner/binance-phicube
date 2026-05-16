## ADDED Requirements

### Requirement: Observabilidade de runtime para ciclos de sinal
O runtime SHALL produzir rastreabilidade estruturada por ciclo de avaliacao de sinal, com campos minimos `symbol`, `timeframe`, `candle_close_time`, `engine_outcome`, `risk_outcome`, `risk_reason` e `final_status`, para suportar diagnostico operacional sem ambiguidade.

#### Scenario: Evento estruturado por ciclo
- **WHEN** um ciclo de monitoramento de candle fechada for processado
- **THEN** o runtime MUST emitir evento estruturado contendo os campos minimos de diagnostico do ciclo

#### Scenario: Ausencia de sinal com continuidade operacional
- **WHEN** nao houver sinal gerado em um ciclo valido
- **THEN** o runtime SHALL registrar `engine_outcome=no_signal` e `final_status=NO_SETUP_DETECTED` sem caracterizar falha tecnica

#### Scenario: Rejeicao por risco com rastreabilidade completa
- **WHEN** houver sinal valido e o risco rejeitar a operacao
- **THEN** o runtime MUST registrar `risk_outcome=rejected`, `risk_reason` e `final_status=REJECTED_BY_RISK`

### Requirement: Superficie operacional para ausencia prolongada de sinais
O sistema MUST expor uma superficie consultavel de diagnostico para diferenciar `NO_SETUP_DETECTED`, `REJECTED_BY_RISK`, `PIPELINE_INTERRUPTED` e `PERSISTENCE_GAP` por simbolo/timeframe no periodo analisado.

#### Scenario: Consulta de diagnostico por simbolo e timeframe
- **WHEN** um operador consultar o estado de geracao de sinais de um simbolo/timeframe
- **THEN** o sistema SHALL retornar a classificacao diagnostica consolidada do periodo com timestamp da ultima evidencia
