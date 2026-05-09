## ADDED Requirements

### Requirement: Dashboard MUST expose multiple market bias views
O dashboard MUST expor um conjunto de visões de bias de mercado derivadas das posições abertas, além da visão legada padrão.

#### Scenario: Snapshot with open positions
- **WHEN** o endpoint `/positions` retornar snapshot com posições abertas
- **THEN** o payload MUST incluir `analysis.bias_views` com lista de visões disponíveis
- **AND** cada visão MUST incluir `id`, `direction`, `confidence`, `score`, `reason` e `metrics`

### Requirement: Legacy bias contract MUST remain available
Para compatibilidade, o campo `analysis.bias` MUST permanecer disponível e representar a visão ativa padrão.

#### Scenario: Existing client reads legacy field
- **WHEN** um cliente legado consumir apenas `analysis.bias`
- **THEN** o contrato atual MUST continuar válido sem campos obrigatórios adicionais

### Requirement: Bias divergence MUST be explicit
Quando visões diferentes apontarem direções distintas, o dashboard MUST sinalizar divergência de forma explícita.

#### Scenario: Divergent view directions
- **WHEN** ao menos duas visões tiverem `direction` diferentes
- **THEN** `analysis.bias_views.divergence.has_divergence` MUST ser `true`
- **AND** `analysis.bias_views.divergence.summary` MUST descrever a divergência

### Requirement: Neutral persistence MUST be explainable
Quando a visão de alocação permanecer em `NEUTRAL/low`, o dashboard MUST expor métricas que permitam auditar o racional.

#### Scenario: Allocation view remains neutral
- **WHEN** a visão `allocation` retornar `NEUTRAL/low`
- **THEN** `metrics` MUST incluir no mínimo `long_exposure`, `short_exposure` e `relative_balance`
- **AND** `reason` MUST explicar que a neutralidade decorre de balanceamento de exposição
