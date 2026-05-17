# Capability: symbol-operational-detail

## ADDED Requirements

### Requirement: Home must list all monitored symbols with operational summary

The system MUST provide a monitoring home listing all monitored symbols with concise operational context.

#### Scenario: Render monitored symbols

- **WHEN** user opens monitoring home
- **THEN** system returns 100% of monitored symbols
- **AND** each item includes `symbol`, `timeframe`, `current_price`, `momentum_summary`,
  `last_analysis_summary`, `risk_status`, `period_pnl`, and `as_of`

#### Scenario: Home interactions

- **WHEN** user applies sort/search/filter
- **THEN** list supports sort by `symbol|pnl|momentum|status`
- **AND** click on symbol navigates to detail page

### Requirement: Symbol snapshot must show current operational position

The system MUST provide a snapshot block that answers where the symbol currently stands.

#### Scenario: Snapshot payload

- **WHEN** symbol detail is opened
- **THEN** snapshot includes `symbol`, `timeframe`, `current_price`, short variation, and `as_of`
- **AND** time contract is UTC

### Requirement: Symbol detail must be exposed through a facade contract

The system MUST expose symbol detail data through a unified facade-style contract.

#### Scenario: Unified detail payload

- **WHEN** symbol detail is requested
- **THEN** response is assembled by a single facade contract
- **AND** contract includes `snapshot`, `risk`, `last_analysis`, `chart`, and `trades_history`
- **AND** all sub-blocks share the same `symbol`, `timeframe`, and `as_of`

### Requirement: Risk traffic-light must be explicit and actionable

The system MUST expose an explicit risk status per symbol to guide capital scaling decisions.

#### Scenario: Risk status contract

- **WHEN** symbol detail is loaded
- **THEN** risk block includes `risk_status` in `ok|atencao|bloqueado`, `risk_flags[]`, and `as_of`

#### Scenario: Risk state transitions

- **WHEN** risk conditions change
- **THEN** state transitions follow explicit model
- **AND** critical triggers may transition directly to `bloqueado`

#### Scenario: State-machine transition integrity

- **WHEN** risk status transition occurs
- **THEN** transition must be one of the allowed transitions
- **AND** invalid transition attempts are rejected or normalized according to policy

### Requirement: Last analysis must include plain human explanation

The system MUST provide plain-language explanation for latest analysis.

#### Scenario: Human explanation fields

- **WHEN** latest analysis is returned
- **THEN** payload includes `classification`, `what_i_saw`, `what_i_decided`, `why`, `next_step`,
  `full_text`, and `as_of`

#### Scenario: Language quality

- **WHEN** explanation is generated
- **THEN** text is concise, non-technical, and short-form (max 4 sentences in summary)

#### Scenario: Template factory consistency

- **WHEN** explanation is generated for a given `classification`
- **THEN** template is selected by deterministic factory mapping
- **AND** unknown classifications fallback to a neutral default template

### Requirement: Operational chart must show watch zones and rationale

The system MUST provide operational chart with current price context and watch zones.

#### Scenario: Chart payload

- **WHEN** chart data is requested
- **THEN** payload includes `candles`, `current_price`, `levels.entry/sl/tp`, `watch_zones[]`, `as_of`

#### Scenario: Watch zone contract

- **WHEN** watch zones are present
- **THEN** each zone includes `zone_id`, `type`, `price_min`, `price_max`, `priority`,
  `why_human`, and `expected_action`
- **AND** `type` is one of `entrada|invalidacao|alvo|observacao`

#### Scenario: Strategy-driven zone evaluation

- **WHEN** watch zones are produced
- **THEN** zone priority and `expected_action` are derived by strategy context
- **AND** strategy context considers at least `timeframe` and regime metadata

### Requirement: Trades history must provide recent operational context

The system MUST provide paginated trade history by symbol with execution context.

#### Scenario: Trades history payload

- **WHEN** trade history is requested in symbol detail
- **THEN** each trade includes `opened_at`, `closed_at`, `side`, `entry_price`, `exit_price`,
  `quantity`, `pnl_usdt`, `status`, `close_reason`, and `as_of`

#### Scenario: Trades history interactions

- **WHEN** user applies filters
- **THEN** history supports pagination and filter by status/period

### Requirement: All blocks must follow global contract coherence

The system MUST enforce coherence across all blocks.

#### Scenario: Coherence rules

- **WHEN** detail payload is assembled
- **THEN** all blocks share `symbol`, `timeframe`, `as_of`
- **AND** numeric fields declare unit/precision semantics consistently

### Requirement: Each block must expose explicit UI states

The system MUST define UI states per block for robust operational reading.

#### Scenario: Block state coverage

- **WHEN** any block renders
- **THEN** block supports `loading`, `empty`, `partial_data`, `error_recoverable`, `stale_data`

### Requirement: Block synchronization must follow observer-style events

The system MUST synchronize block refreshes through explicit event notifications.

#### Scenario: Event-based updates

- **WHEN** any core data domain is updated (`risk`, `analysis`, `chart`, `trades`)
- **THEN** corresponding UI blocks receive a specific update event
- **AND** non-affected blocks do not require full-page refresh
