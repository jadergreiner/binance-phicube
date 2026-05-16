# slippage-protection Specification

## Purpose
TBD - created by archiving change spec-043-slippage-protection. Update Purpose after archive.
## Requirements
### Requirement: Protective stop orders SHALL use price protection
The exchange adapter SHALL include `priceProtect: True` when creating `STOP_MARKET` and `TAKE_PROFIT_MARKET` protective orders.

#### Scenario: Stop-loss order payload includes price protection
- **WHEN** the system builds params for `create_stop_loss_order`
- **THEN** params MUST include `priceProtect` set to `True`

#### Scenario: Take-profit order payload includes price protection
- **WHEN** the system builds params for `create_take_profit_order`
- **THEN** params MUST include `priceProtect` set to `True`

### Requirement: Risk evaluation SHALL enforce slippage-aware tolerance
The risk engine SHALL estimate slippage and reject trades when `(actual_risk_usdt + slippage_estimate_usdt)` exceeds `risk_per_trade_usdt * slippage_tolerance_multiplier`.

#### Scenario: Reject trade when slippage-adjusted risk exceeds tolerance
- **GIVEN** a candidate trade with computed `actual_risk_usdt` and `slippage_estimate_usdt`
- **WHEN** `total_risk_usdt` is above configured tolerance
- **THEN** calculation MUST return rejection with code `SLIPPAGE_EXCEEDS_TOLERANCE`

#### Scenario: Use safe fallback tier for unknown symbols
- **WHEN** symbol is missing from liquidity map
- **THEN** slippage strategy MUST use fallback tier `medium`

### Requirement: Consecutive-loss circuit breaker SHALL reduce risk statefully
The risk engine SHALL track consecutive losses and reduce active risk-per-trade when threshold is reached, resetting after configured recovery wins.

#### Scenario: Activate reduced-risk state after threshold losses
- **WHEN** consecutive losses reach configured threshold
- **THEN** circuit breaker MUST transition to reduced-risk state and apply reduction factor

#### Scenario: Reset reduced-risk state after recovery wins
- **GIVEN** circuit breaker is active
- **WHEN** required consecutive wins are reached
- **THEN** circuit breaker MUST restore baseline risk and clear counters

### Requirement: Position clamp SHALL support balance percentage cap
The risk engine SHALL clamp max position by combining absolute max position with percentage-of-balance cap.

#### Scenario: Effective cap uses min between absolute and percentage limits
- **WHEN** both absolute and percentage limits are enabled
- **THEN** effective max position MUST be `min(max_position_usdt, balance * max_position_pct / 100)`

