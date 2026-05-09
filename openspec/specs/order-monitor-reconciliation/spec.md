# order-monitor-reconciliation Specification

## Purpose
TBD - created by archiving change order-monitor-consistency-hardening. Update Purpose after archive.
## Requirements
### Requirement: Symbol normalization for position reconciliation

O sistema MUST normalizar identificadores de símbolo antes de comparar posição registrada no trade e posição retornada pela exchange.

#### Scenario: Equivalent symbols with different formats

- **WHEN** um trade estiver com símbolo `ATOMUSDT` e a exchange retornar `ATOM/USDT:USDT`
- **THEN** o monitor MUST tratá-los como o mesmo ativo para decisão de posição aberta

### Requirement: Two-cycle confirmation before manual close

O sistema MUST exigir confirmação de posição ausente em 2 ciclos consecutivos antes de classificar fechamento manual.

#### Scenario: Single-cycle temporary absence

- **WHEN** a posição não for detectada em apenas um ciclo
- **THEN** o monitor MUST registrar estado pendente e MUST NOT encerrar o trade como manual nesse ciclo

#### Scenario: Consecutive absence confirmation

- **WHEN** a posição não for detectada em 2 ciclos consecutivos
- **THEN** o monitor MUST permitir fluxo de fechamento manual

### Requirement: Robust fallback on OrderNotFound

O sistema MUST tratar `OrderNotFound` como evidência insuficiente isolada e MUST executar fallback robusto de confirmação de estado antes de encerrar trade.

#### Scenario: OrderNotFound with open position evidence

- **WHEN** ocorrer `OrderNotFound` e houver evidência de posição ainda aberta
- **THEN** o monitor MUST manter o trade aberto e MUST registrar evento de reconciliação inconclusiva

#### Scenario: OrderNotFound with confirmed absent position

- **WHEN** ocorrer `OrderNotFound` e a ausência de posição for confirmada conforme regra de 2 ciclos
- **THEN** o monitor MAY seguir para fechamento manual com marcação auditável

### Requirement: Auditability of manual close confirmation

O sistema MUST registrar telemetria estruturada para decisões de fechamento manual confirmadas por reconciliação.

#### Scenario: Manual close confirmed by reconciliation

- **WHEN** um trade for encerrado manualmente após confirmação robusta
- **THEN** o sistema MUST persistir metadados mínimos de confirmação (ciclos de confirmação, evidência de posição ausente e origem da decisão)

