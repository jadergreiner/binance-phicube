## 0. Scope Decisions

- [x] 0.1 Confirm policy baseline for sensitive fields (`omit` as default, `mask` as opt-in)
- [x] 0.2 Decide whether `BacktestTrade`/`BacktestResult` stay in this change or move to follow-up change

## 1. Serialization Core Setup

- [x] 1.1 Create `src/common/serialization.py` with `Serializable` protocol and `@auto_dict` decorator
- [x] 1.2 Implement validation guard so `@auto_dict` fails clearly when used on non-dataclass targets
- [x] 1.3 Implement recursive handling for nested `to_dict()` objects and lists of serializable items
- [x] 1.4 Implement sensitive-field protection policy (Strategy: `omit`/`mask`) for secret-like keys
- [x] 1.5 Add explicit adapter path for non-serializable external types used by model fields

## 2. Dataclass Migration

- [x] 2.1 Refactor `Signal` to use `@auto_dict` and remove duplicated manual serialization where compatible
- [x] 2.2 Refactor `PositionSize` to use `@auto_dict` and preserve payload compatibility
- [x] 2.3 Refactor `Trade` to use `@auto_dict` and preserve payload compatibility
- [x] 2.4 Refactor `SignalEventData` (substitui `SignalEvaluation` no estado atual) to use `@auto_dict` and preserve payload compatibility
- [x] 2.5 Evaluate and apply optional migration for backtest dataclasses (`BacktestTrade`/`BacktestResult`) if scope remains valid

## 3. Validation and Regression Safety

- [x] 3.1 Add unit tests in `tests/common/test_serialization.py` for generation, recursion, list handling, and invalid usage
- [x] 3.2 Add tests validating strategy swap (`omit` vs `mask`) without model code changes
- [x] 3.3 Add tests for adapter-based serialization of non-native field types
- [x] 3.4 Add parity tests ensuring migrated models keep expected output keys/types versus previous behavior
- [x] 3.5 Add regression tests for datetime field format compatibility in migrated models
- [x] 3.6 Add deterministic failure test for cyclic reference serialization
- [x] 3.7 Add parity tests for optional `None` field inclusion behavior
- [x] 3.8 Execute targeted strategy/trading/backtest test suites to verify no serialization regressions
- [x] 3.9 Review final output against `docs/SDD/SPEC_040_SERIALIZABLE_PROTOCOL/SPEC.md` and update task states
