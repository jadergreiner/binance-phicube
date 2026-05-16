# predictive-circuit-breaker Specification

## Purpose
TBD - created by archiving change spec-044-predictive-circuit-breaker. Update Purpose after archive.
## Requirements
### Requirement: Predictive pre-trade risk gate for low-liquidity symbols
The risk evaluation pipeline MUST execute a predictive circuit breaker before final trade approval. The gate SHALL evaluate current relative volatility (`ATR/close`) against a configurable historical percentile threshold and MUST block the cycle when the symbol liquidity tier is eligible and the threshold is exceeded.

#### Scenario: Skip cycle when low-liquidity threshold is exceeded
- **WHEN** a symbol is mapped to an eligible tier and current `ATR/close` is greater than the configured percentile threshold computed from recent history
- **THEN** the system MUST reject trade approval for that cycle with explicit predictive-circuit-breaker reason

#### Scenario: Allow cycle when threshold is not exceeded
- **WHEN** a symbol is mapped to an eligible tier and current `ATR/close` is less than or equal to the configured percentile threshold
- **THEN** the predictive gate MUST NOT reject the trade and the normal risk pipeline MUST continue

### Requirement: Pattern-oriented risk gate architecture
The predictive circuit breaker implementation MUST follow a pattern-oriented design where evaluation logic is isolated as a strategy and executed as part of an ordered risk-gate chain.

#### Scenario: Strategy encapsulates predictive rule
- **WHEN** predictive blocking criteria are evaluated
- **THEN** the system MUST execute the rule through a dedicated strategy component instead of embedding the full rule directly in orchestration code

#### Scenario: Predictive gate participates in ordered chain
- **WHEN** risk gates are processed for a trade decision
- **THEN** the system MUST evaluate gates in deterministic order and stop the chain immediately when a gate rejects the cycle

### Requirement: Tier-scoped activation and safe fallback behavior
The predictive circuit breaker MUST apply only to configured liquidity tiers and MUST fail safe for invalid or insufficient input data by not blocking the trade solely due to data quality errors.

#### Scenario: Non-eligible tier bypasses predictive block
- **WHEN** the symbol liquidity tier is not listed in predictive-breaker eligible tiers
- **THEN** the predictive gate MUST return pass and MUST NOT block the cycle

#### Scenario: Invalid data does not cause false block
- **WHEN** required values are invalid or insufficient to compute a reliable percentile threshold
- **THEN** the system MUST bypass predictive blocking for that cycle and MUST continue with remaining risk checks

### Requirement: Structured observability for predictive skips
The system MUST emit structured telemetry whenever a cycle is blocked by the predictive circuit breaker, including fields required for operational audit and dashboard aggregation.

#### Scenario: Structured event is emitted on predictive skip
- **WHEN** the predictive gate blocks a cycle
- **THEN** the system MUST emit a structured event containing at least symbol, liquidity tier, current atr-ratio, computed threshold, and skip reason

#### Scenario: Skip counter is available for dashboard consumption
- **WHEN** predictive skips occur during runtime
- **THEN** the system MUST expose an aggregate counter of predictive skipped cycles/trades through the existing observability surface consumed by the dashboard

#### Scenario: Observer integration publishes skip event
- **WHEN** a predictive skip is produced by the risk chain
- **THEN** the system MUST notify observability subscribers through an event publication boundary decoupled from core risk decision logic

### Requirement: Configurable thresholds without code change
Predictive circuit breaker behavior MUST be configurable via runtime settings, including percentile value, historical window size, and eligible liquidity tiers.

#### Scenario: Operator changes percentile threshold via configuration
- **WHEN** runtime configuration is updated with a new predictive percentile value
- **THEN** subsequent risk evaluations MUST use the updated percentile threshold without requiring source-code changes

#### Scenario: Operator restricts eligible tiers via configuration
- **WHEN** runtime configuration narrows predictive eligible tiers
- **THEN** symbols outside the configured tier set MUST no longer be blocked by the predictive gate

