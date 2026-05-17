# Two-Stage Policy

## Stage 1: Refiner (Specification Only)

Allowed:

- Clarify objective, scope, constraints, risks.
- Produce structured specification and acceptance criteria.
- Define implementation tasks and sequencing.

Forbidden:

- Writing or editing source code.
- Running implementation commands.
- Merging implementation decisions without explicit approval.

Exit criteria:

- SDD stages 1..6 completed (see `sdd/sdd-6-stage.policy.md`)
- Artifact lint gate passed (see `workflow/artifact-lint-gate.policy.md`)
- Human approval recorded.
- Handoff checklist passed.

## Stage 2: Executor (Implementation)

Allowed:

- Implement approved tasks from the refiner spec.
- Run validations and tests.
- Report deviations and blockers.

Forbidden:

- Expanding scope without returning to Stage 1.
- Ignoring defined constraints and acceptance criteria.

Exit criteria:

- Implementation finished.
- Acceptance template completed.
- Artifact lint gate passed for modified artifacts.
- Results mapped to original spec.

## Mandatory Gate

No code implementation before:

1) Refiner SDD 6-stage flow complete
2) Explicit human approval
3) Handoff checklist approved
4) Artifact lint gate PASS
