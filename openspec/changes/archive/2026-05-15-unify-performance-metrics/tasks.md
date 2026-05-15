## 1. Shared Metrics Core

- [x] 1.1 Create shared metrics module in `src/common/` with unified metric calculation entrypoint
- [x] 1.2 Implement deterministic calculation for `total_trades`, `win_rate_pct`, `total_pnl_usdt`, `avg_rrr`, `max_drawdown_usdt`, and `profit_factor`
- [x] 1.3 Enforce semantic compatibility rules (`profit_factor=0.0` when `gross_loss==0`; drawdown non-positive)
- [x] 1.4 Add unit tests for empty dataset, mixed wins/losses, no-loss dataset, and drawdown sign convention

## 2. Repository Integration

- [x] 2.1 Refactor `src/storage/repository.py::_calc_metrics` to extract normalized inputs and call the shared metrics core
- [x] 2.2 Preserve repository-specific ordering behavior by `closed_at` before metric computation
- [x] 2.3 Verify existing storage metrics tests remain behaviorally compatible

## 3. Backtest Integration

- [x] 3.1 Refactor `src/backtest/engine.py::_calc_metrics` to call the shared metrics core
- [x] 3.2 Refactor metric-building logic in `BacktestEngine._build_result` to reuse the same core with selected `pnl_field`
- [x] 3.3 Confirm compatibility for `pnl_usdt`, `pnl_gross_usdt`, and `pnl_net_usdt` result flows

## 4. Regression and Cleanup

- [x] 4.1 Execute targeted backtest and storage test suites for metric parity
- [x] 4.2 Remove residual duplicated metric formulas from repository and backtest paths
- [x] 4.3 Validate final behavior against SPEC_039 expectations and change specs before apply handoff
