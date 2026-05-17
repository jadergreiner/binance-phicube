# T09 Rollout Gates - PhiCube

## Objective

Control promotion path `shadow -> advisory -> active` with explicit gates,
evidence, and human approvals.

## Mode Policy

- `shadow`: signal generation allowed, execution blocked.
- `advisory`: signal generation allowed, execution blocked.
- `active`: signal generation and execution allowed (subject to risk gates).

## Promotion Gates

| Gate ID | Promotion | Required evidence | Decision owner | Status |
| --- | --- | --- | --- | --- |
| RG-T09-01 | none -> shadow | T01..T08 completed, lint/tests PASS, T09 mode blocking implemented | Human + E1 | PASS |
| RG-T09-02 | shadow -> advisory | no regressions in diagnostics payload and cycle logs | Human + E1/E6 | READY |
| RG-T09-03 | advisory -> active (canary) | contract/integration tests PASS, mode gate behavior verified, rollback path documented | Human + E1/E2/E6 | READY |
| RG-T09-04 | active canary -> broader active | canary monitoring window accepted by human, no critical incidents | Human + E1/E6 | PENDING |

## Rollback Rule

- Immediate rollback by setting `PHICUBE_MODE=shadow` and preserving
  `PHICUBE_ENABLED=true` for diagnostic continuity.

## Evidence Reference

- `executor-submissions/T08-submission.md`
- `executor-submissions/T09-submission.md`
