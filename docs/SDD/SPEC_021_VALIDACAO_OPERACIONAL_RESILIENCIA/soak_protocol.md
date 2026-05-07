# Soak Protocol - SPEC_021

## Objective

Run a controlled 48h operational validation cycle with objective pass/fail output.

## Preconditions

1. Bot and API containers are healthy and stable before start.
2. `.env` is present with non-production credentials.
3. MongoDB is reachable and writable.
4. Monitoring logs are enabled for bot and API.
5. Baseline tests pass before the soak window starts.

## Mandatory Events to Capture

1. Startup success for bot and API.
2. At least one full monitoring loop for each configured symbol.
3. Heartbeat/health endpoint responses at fixed intervals.
4. Error and retry events (if any), including recovery evidence.
5. Shutdown behavior at end of window.

## Interruption Criteria

Stop and mark `reproved` immediately if any condition occurs:

1. Process crash with no automatic recovery.
2. Position/order safety violation.
3. Persistent health endpoint failure for more than 5 minutes.
4. Secret/token exposure in logs or generated evidence.

## Evidence Format

Use `soak_evidence.template.json` as the canonical output format.
All evidence files must be stored under:

`docs/SDD/SPEC_021_VALIDACAO_OPERACIONAL_RESILIENCIA/evidence/`

## Pass/Fail Rule

- `approved` only if:
  - full 48h completed;
  - no interruption criteria triggered;
  - required events captured.
- `reproved` otherwise, with explicit `failure_reason`.
