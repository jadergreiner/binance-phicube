## Why

The exchange layer currently relies on informal interfaces and `Any`-typed clients in critical trading paths, which weakens static validation and increases integration risk. This change formalizes a single contract now to prevent runtime incompatibilities as the codebase expands to additional client implementations.

## What Changes

- Introduce a new abstract contract `TradingClient` in `src/exchange/base_client.py` with typed async methods for lifecycle, market data, balance, leverage, orders, positions, and precision.
- Update `BinanceClient` and `SimulatedBinanceClient` to implement the shared `TradingClient` contract.
- Replace `Any`-typed client dependencies with `TradingClient` in core consumers (`OrderManager`, runtime monitor registry in `src/main.py`, and order monitor where applicable).
- Keep behavior-compatible defaults for optional capabilities (`validate_market_liquidity`, `fetch_quantity_precision_map`) to avoid unnecessary runtime regressions.

## Capabilities

### New Capabilities
- `trading-client-abc`: Defines and enforces a typed abstract exchange client contract used by both real and simulated trading clients and by downstream trading components.

### Modified Capabilities
- None.

## Impact

- Affected code: `src/exchange/base_client.py` (new), `src/exchange/binance_client.py`, `src/exchange/simulated_client.py`, `src/trading/order_manager.py`, `src/main.py`, and `src/monitoring/order_monitor.py` (if typed client is present).
- API impact: No external API contract changes; internal Python type contracts become explicit.
- Dependencies/systems: Type-checking and test confidence improve for exchange integration paths.
