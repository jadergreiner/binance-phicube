## ADDED Requirements

### Requirement: Centralized Performance Metrics Core
The system SHALL provide a single reusable metrics core that computes `total_trades`, `win_rate_pct`, `total_pnl_usdt`, `avg_rrr`, `max_drawdown_usdt`, and `profit_factor` from normalized trade data.

#### Scenario: Compute metrics from normalized numeric sequences
- **WHEN** a caller provides normalized PnL and RRR sequences for a closed-trade set
- **THEN** the system MUST compute all six metrics using one shared calculation path

#### Scenario: Empty dataset returns neutral metrics
- **WHEN** the caller provides an empty trade dataset
- **THEN** the system MUST return zeroed metrics (`total_trades=0`, numeric metrics `0.0`)

### Requirement: Semantic Compatibility for Profit Factor and Drawdown
The system SHALL preserve current operational semantics for profit factor and drawdown to maintain historical comparability.

#### Scenario: Profit factor with no losses
- **WHEN** gross loss equals zero
- **THEN** the system MUST return `profit_factor = 0.0`

#### Scenario: Drawdown sign convention
- **WHEN** max drawdown is reported
- **THEN** the system MUST return `max_drawdown_usdt` as a non-positive value (`<= 0.0`)

### Requirement: Context-specific Data Extraction with Shared Math
The system SHALL keep context-specific extraction at call sites while reusing the same metrics core for production and backtest.

#### Scenario: Repository path uses shared core
- **WHEN** production metrics are computed from Mongo trade documents
- **THEN** the repository MUST extract context fields (including ordering) and invoke the shared metrics core

#### Scenario: Backtest path uses shared core for multiple PnL fields
- **WHEN** backtest metrics are computed for `pnl_usdt`, `pnl_gross_usdt`, or `pnl_net_usdt`
- **THEN** the backtest engine MUST invoke the same shared metrics core after extracting values for the selected field

### Requirement: Eliminate Divergent Metric Implementations
The system SHALL not maintain multiple independent formulas for the six core metrics in repository and backtest paths.

#### Scenario: Build result path reuses shared core
- **WHEN** `BacktestEngine._build_result` composes final result metrics
- **THEN** it MUST reuse the shared metrics core rather than reimplementing formulas inline

#### Scenario: Regression parity with existing behavior
- **WHEN** existing storage and backtest regression suites are executed
- **THEN** metric outputs MUST remain behaviorally compatible with current expectations
