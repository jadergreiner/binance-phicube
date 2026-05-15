## ADDED Requirements

### Requirement: Trading client contract SHALL be explicit and complete
The system SHALL define an abstract `TradingClient` contract that centralizes required exchange operations for lifecycle, market data, balance, leverage, orders, positions, and precision.

#### Scenario: Contract completeness is enforced
- **WHEN** a concrete trading client class is instantiated without implementing required abstract methods
- **THEN** the system MUST raise an instantiation error indicating incomplete contract implementation

### Requirement: Trading client implementations SHALL be substitutable
`BinanceClient` and `SimulatedBinanceClient` SHALL implement `TradingClient` so either implementation can be injected into trading consumers without consumer code changes.

#### Scenario: Runtime substitution between concrete clients
- **WHEN** a consumer receives either `BinanceClient` or `SimulatedBinanceClient` typed as `TradingClient`
- **THEN** the consumer MUST execute the same integration flow through the shared contract methods

### Requirement: Consumers SHALL depend on TradingClient instead of Any
Critical consumers (`OrderManager`, runtime monitor registry, and order monitor where applicable) SHALL type their client dependency as `TradingClient`.

#### Scenario: Type-safe dependency in consumer constructors
- **WHEN** a consumer is instantiated with an object that does not satisfy `TradingClient`
- **THEN** static type checking MUST report incompatibility before deployment

### Requirement: Optional capabilities SHALL have safe defaults in base contract
The base contract SHALL provide default non-breaking implementations for optional methods `validate_market_liquidity` and `fetch_quantity_precision_map`.

#### Scenario: Optional methods used by a new client implementation
- **WHEN** a new concrete client does not override optional capability methods
- **THEN** the default base behavior MUST execute without raising errors
