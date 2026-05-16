## MODIFIED Requirements

### Requirement: Centralized Performance Metrics Core
The system SHALL provide a single reusable metrics core that computes `total_trades`, `win_rate_pct`, `total_pnl_usdt`, `avg_rrr`, `max_drawdown_usdt`, and `profit_factor` from normalized trade data.

#### Scenario: Compute metrics from normalized numeric sequences
- **WHEN** a caller provides normalized PnL and RRR sequences for a closed-trade set
- **THEN** the system MUST compute all six metrics using one shared calculation path

#### Scenario: Empty dataset returns neutral metrics
- **WHEN** the caller provides an empty trade dataset
- **THEN** the system MUST return zeroed metrics (`total_trades=0`, numeric metrics `0.0`)

### Requirement: Context-specific Data Extraction with Shared Math
The system SHALL keep context-specific extraction at call sites while reusing the same metrics core for production and backtest.

#### Scenario: Repository path uses shared core
- **WHEN** production metrics are computed from Mongo trade documents
- **THEN** the repository MUST extract context fields (including ordering) and invoke the shared metrics core

#### Scenario: Backtest path uses shared core for multiple PnL fields
- **WHEN** backtest metrics are computed for `pnl_usdt`, `pnl_gross_usdt`, or `pnl_net_usdt`
- **THEN** the backtest engine MUST invoke the same shared metrics core after extracting values for the selected field

#### Scenario: Assertiveness aggregations reuse shared core
- **WHEN** dashboard assertiveness metrics are computed by symbol and period
- **THEN** the system MUST reuse the shared metrics core for win-rate, PnL, drawdown, and profit-factor components

## ADDED Requirements

### Requirement: Signal-to-Trade Conversion Metric
The system SHALL compute and expose signal conversion metrics for dashboard assertiveness analysis.

#### Scenario: Conversion rate calculation
- **WHEN** total signals and total executed trades are available in a filtered period
- **THEN** the system MUST compute `signal_to_trade_conversion_pct = (total_trades / total_signals) * 100` with safe zero-division handling

#### Scenario: No signals in period
- **WHEN** total signals equals zero in the selected period
- **THEN** the system MUST return `signal_to_trade_conversion_pct = 0.0`

### Requirement: Repository Boundary for Assertiveness Inputs
The system SHALL keep signal/trade extraction for assertiveness metrics behind repository interfaces, preserving separation between data access and metric calculation.

#### Scenario: Facade consumes repository-level inputs
- **WHEN** assertiveness metrics are assembled for API response
- **THEN** the application layer MUST consume repository-provided datasets and apply shared math without direct storage coupling in the route
