# signal-engine-isolation Specification

## Purpose
TBD - created by archiving change spec-045-isolamento-signal-engine. Update Purpose after archive.
## Requirements
### Requirement: Boundary isolado para avaliação de sinal
O sistema SHALL expor um boundary explícito para avaliação de sinal, com contrato estável de entrada e saída desacoplado da orquestração operacional.

#### Scenario: Avaliação via contrato dedicado
- **WHEN** o orquestrador solicitar a avaliação de sinal para um par e candle fechado
- **THEN** a avaliação MUST ocorrer por meio do contrato isolado, sem acesso direto a detalhes de execução de ordens

### Requirement: Adaptador único para invocação do SignalEngine
O sistema SHALL usar um adaptador único para invocar o `SignalEngine`, centralizando validação básica de entrada, normalização de retorno e captura de falhas.

#### Scenario: Retorno normalizado em sucesso
- **WHEN** o `SignalEngine` retornar decisão válida de sinal
- **THEN** o adaptador MUST normalizar o resultado para o formato de decisão definido no contrato

#### Scenario: Falha controlada na avaliação
- **WHEN** ocorrer exceção durante a avaliação do `SignalEngine`
- **THEN** o adaptador MUST retornar ausência de sinal segura e registrar evento de observabilidade sem interromper o loop do bot

### Requirement: Compatibilidade comportamental com decisões existentes
O sistema SHALL preservar a semântica atual de decisão de sinal (`LONG`, `SHORT` ou ausência de sinal), garantindo compatibilidade com os módulos de risco e ordem.

#### Scenario: Encaminhamento de decisão LONG/SHORT
- **WHEN** a avaliação produzir `LONG` ou `SHORT`
- **THEN** a decisão MUST ser encaminhada sem alteração semântica para os módulos subsequentes

#### Scenario: Ausência de sinal
- **WHEN** a avaliação não identificar condição de entrada
- **THEN** o sistema MUST manter o fluxo sem criação de ordem e sem efeitos colaterais adicionais

### Requirement: Testabilidade determinística do contrato isolado
O sistema SHALL disponibilizar comportamento testável do boundary isolado por meio de testes unitários independentes de exchange, banco e rede.

#### Scenario: Teste unitário sem infraestrutura externa
- **WHEN** os testes do contrato de sinal forem executados em CI local
- **THEN** os testes MUST validar entradas, saídas e tratamento de erro sem dependências externas

