## ADDED Requirements

### Requirement: Camada ML auxiliar em shadow mode sem impacto operacional
O runtime SHALL executar a camada de apoio ML em modo shadow para gerar diagnostico auxiliar sem alterar a decisao operacional do BO Williams nem o fluxo de execucao de ordens.

#### Scenario: Shadow mode ativo preserva execucao real
- **WHEN** a feature `ml_support_enabled=true` e `ml_support_shadow_mode=true` estiver ativa
- **THEN** o sistema MUST calcular score e decisao auxiliar ML
- **AND** o sistema MUST manter a execucao real guiada apenas pelo resultado BO atual
- **AND** o sistema MUST nao bloquear nem forcar ordem com base na decisao ML

#### Scenario: Falha da inferencia nao interrompe ciclo
- **WHEN** ocorrer timeout, erro de modelo ou erro de serializacao na inferencia ML
- **THEN** o ciclo de sinal SHALL continuar com fallback para BO puro
- **AND** o sistema MUST registrar evento de falha da camada ML para auditoria

### Requirement: Feature flags por simbolo e timeframe para rollout seguro
O sistema MUST suportar habilitacao controlada da camada ML por configuracao global e por simbolo/timeframe, com desativacao imediata sem necessidade de alterar contratos de trade.

#### Scenario: Flag global desativada
- **WHEN** `ml_support_enabled=false`
- **THEN** o sistema MUST nao executar inferencia ML no ciclo
- **AND** o diagnostico SHALL indicar camada ML inativa

#### Scenario: Canary por simbolo/timeframe
- **WHEN** `ml_support_enabled=true` e apenas subset de simbolos/timeframes estiver permitido
- **THEN** o sistema MUST executar inferencia apenas no conjunto permitido
- **AND** o sistema SHALL manter comportamento BO puro para os demais ativos

### Requirement: Diagnostico operacional com campos ML rastreaveis
O sistema MUST persistir campos minimos de diagnostico ML por ciclo para comparacao BO vs apoio ML e analise de impacto.

#### Scenario: Persistencia de campos minimos ML
- **WHEN** um ciclo de sinal for concluido com camada ML habilitada
- **THEN** o diagnostico MUST incluir `ml_enabled`, `ml_shadow_mode`, `ml_score`, `ml_decision`, `ml_reason` e `ml_model_version`
- **AND** os campos MUST ser opcionais e retrocompativeis para ciclos legados

#### Scenario: Exposicao em endpoint de diagnostico
- **WHEN** um operador consultar o diagnostico por simbolo/timeframe
- **THEN** a API SHALL retornar os campos ML persistidos no ultimo ciclo disponivel
- **AND** a ausencia de campos legados nao deve gerar erro de contrato

### Requirement: Gate de promocao com criterios objetivos de go/no-go
A promocao de shadow mode para qualquer impacto operacional da camada ML MUST depender de criterios objetivos de desempenho e risco contra baseline BO puro.

#### Scenario: Criterios minimos para go
- **WHEN** a janela de avaliacao definida for concluida
- **THEN** a promocao so pode ocorrer se expectativa melhorar no minimo 10 por cento e drawdown reduzir no minimo 15 por cento
- **AND** nao houver degradacao relevante de latencia ou disponibilidade

#### Scenario: Bloqueio por no-go
- **WHEN** os criterios minimos nao forem atingidos ou houver instabilidade por drift
- **THEN** a camada ML MUST permanecer em shadow mode
- **AND** a operacao SHALL continuar exclusivamente com BO puro
