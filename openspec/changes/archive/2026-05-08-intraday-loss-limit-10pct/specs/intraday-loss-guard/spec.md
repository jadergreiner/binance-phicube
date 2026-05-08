## ADDED Requirements

### Requirement: Intraday loss threshold blocks new entries
O sistema MUST bloquear novas entradas quando a perda intraday acumulada atingir ou exceder 10% do capital de referência diário.

#### Scenario: Threshold reached
- **WHEN** a perda intraday acumulada for maior ou igual a 10% do capital de referência diário
- **THEN** o sistema MUST rejeitar novas entradas com motivo explícito `intraday_loss_limit_reached`

### Requirement: Existing positions remain managed
Ao atingir o limite intraday, o sistema MUST continuar monitorando e gerenciando posições já abertas conforme regras existentes.

#### Scenario: Open positions after lock
- **WHEN** o bloqueio intraday estiver ativo e houver posições abertas
- **THEN** o sistema MUST manter execução de monitoramento e regras de proteção das posições existentes

### Requirement: Daily reset of entry lock
O sistema MUST restaurar elegibilidade de novas entradas no início do próximo dia operacional.

#### Scenario: Next operational day starts
- **WHEN** ocorrer a virada para novo dia operacional
- **THEN** o bloqueio de novas entradas MUST ser removido e a contagem de perda intraday MUST reiniciar

### Requirement: Auditability of block decisions
O sistema MUST registrar telemetria de bloqueio contendo perda acumulada, threshold e capital de referência para auditoria.

#### Scenario: Entry blocked by intraday loss guard
- **WHEN** uma entrada for bloqueada pela regra intraday
- **THEN** o sistema MUST emitir evento/log estruturado com campos mínimos `intraday_loss_pct`, `threshold_pct` e `daily_reference_capital`
