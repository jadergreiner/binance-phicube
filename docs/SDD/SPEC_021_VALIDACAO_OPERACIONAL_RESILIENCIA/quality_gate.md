# Quality Gate - SPEC_021

## Command

```bash
pytest --cov=src --cov-report=term-missing --cov-report=json:reports/coverage.json
```

## Minimum Coverage Thresholds (critical modules)

- `src/strategy/indicators.py`: 90%
- `src/strategy/signal_engine.py`: 85%
- `src/trading/risk_manager.py`: 80%
- `src/trading/order_manager.py`: 75%
- `src/storage/repository.py`: 75%

## Gate Rule

- `pass`: all thresholds met.
- `fail`: at least one module under threshold or coverage report unavailable.

## Output Contract

Script output file:

`reports/spec021_quality_gate.json`

Schema:

```json
{
  "status": "pass|fail",
  "thresholds": {
    "path": 0.0
  },
  "actual": {
    "path": 0.0
  },
  "failures": [
    "module below threshold"
  ]
}
```
