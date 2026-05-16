## ADDED Requirements

### Requirement: Filtro de assertividade por símbolo e período
O sistema SHALL disponibilizar consulta de assertividade com filtros por símbolo, timeframe e período (`7d`, `30d`, `90d`, `custom`).

#### Scenario: Consulta com período pré-definido
- **WHEN** o usuário solicitar assertividade com `period=30d`
- **THEN** o sistema MUST retornar métricas agregadas apenas para os dados dentro da janela dos últimos 30 dias

#### Scenario: Consulta com período customizado
- **WHEN** o usuário informar `start` e `end` válidos no filtro custom
- **THEN** o sistema MUST retornar métricas restritas ao intervalo informado

### Requirement: Ranking por símbolo para decisão gerencial
O sistema SHALL retornar ranking por símbolo com métricas de assertividade e risco para ordenação operacional.

#### Scenario: Ranking por assertividade
- **WHEN** o usuário solicitar ranking por símbolo no período selecionado
- **THEN** o sistema MUST incluir `assertiveness_pct`, `total_signals`, `total_trades`, `signal_to_trade_conversion_pct`, `pnl_usdt`, `profit_factor` e `max_drawdown_usdt`

#### Scenario: Ranking ordenável
- **WHEN** o usuário selecionar critério de ordenação por `assertiveness_pct` ou `pnl_usdt`
- **THEN** o sistema MUST aplicar ordenação consistente no resultado

### Requirement: Evolução temporal de assertividade
O sistema SHALL expor série temporal de assertividade para análise de tendência no período selecionado.

#### Scenario: Série temporal diária
- **WHEN** o usuário consultar período até 30 dias
- **THEN** o sistema MUST retornar buckets diários com assertividade e PnL por bucket

#### Scenario: Série temporal semanal
- **WHEN** o usuário consultar período superior a 30 dias
- **THEN** o sistema MUST permitir agregação semanal com os mesmos indicadores

### Requirement: Visualização canônica no dashboard
O sistema SHALL exibir a visão de assertividade no frontend canônico servido por `dashboard-api`.

#### Scenario: Filtros refletidos na UI
- **WHEN** o usuário alterar símbolo/timeframe/período
- **THEN** o frontend MUST recarregar resumo, ranking e evolução temporal com os novos filtros

#### Scenario: Persistência de preferências de consulta
- **WHEN** o usuário salvar a visão atual
- **THEN** o frontend MUST persistir as preferências e restaurá-las em nova sessão

### Requirement: Arquitetura orientada a patterns para assertividade
O sistema SHALL implementar a capacidade de assertividade com padrões explícitos para extensibilidade e baixo acoplamento.

#### Scenario: Seleção de período via Strategy
- **WHEN** a API receber um filtro de período (`7d`, `30d`, `90d`, `custom`)
- **THEN** a resolução da janela MUST ocorrer por estratégia dedicada, sem condicional dispersa entre rota e repositório

#### Scenario: Orquestração via Facade com saída em DTO
- **WHEN** uma consulta de assertividade for processada
- **THEN** a rota MUST delegar a orquestração para um facade e retornar DTOs adaptados para o contrato público da API
