# SDD 6-Stage Policy

This policy is mandatory for Stage 1 (Refiners).
It applies to RCA and New Implementation paths.
Q&A path is consultative and does not require full 6-stage flow
unless human requests SPEC/Tasks generation.

## Stages

1. High-level Task

- Free-form problem statement and intended outcome.

1. Standardized Task

- Normalize stage 1 into a fixed template.

1. PRD

- Product requirements and success criteria.

1. SPECs

- Functional and technical specifications.
- Must use `sdd/stages/04-specs.template.md` as the mandatory minimum structure.

1. Plan

- Sequenced execution strategy and dependencies.

1. Tasks

- Actionable implementation task list.

## Core Rules

- Stage 1 can be free-form.
- Stages 2..6 must follow standard templates.
- No stage advances without formal human approval.
- All stage artifacts must be persisted.
- Stage approval is allowed only with artifact lint gate `PASS`.
- Refiners ask questions, analyze, and suggest (human-in-the-loop).
- Filling SDD artifacts is a shared cross-layer skill (Business, Architecture, Governance).
- Lint verification is a shared cross-layer skill (`artifact-lint-gate`).

## Shared Skill Requirement

Name:

- `sdd-artifact-filling` (shared)

Responsibility:

- Fill and normalize SDD stage artifacts (1..6) using approved templates.
- For Stage 4, preserve the minimum SPEC section structure
  exactly as defined in `sdd/stages/04-specs.template.md`.
- Keep traceability between stage outputs and approval records.

Constraint:

- This shared skill structures artifacts only. It does not authorize coding.

## Persistence Standard

Default path per cycle:

- `docs/sdd-cycles/<cycle-id>/01-high-level.md`
- `docs/sdd-cycles/<cycle-id>/02-standardized-task.md`
- `docs/sdd-cycles/<cycle-id>/03-prd.md`
- `docs/sdd-cycles/<cycle-id>/04-specs.md`
- `docs/sdd-cycles/<cycle-id>/05-plan.md`
- `docs/sdd-cycles/<cycle-id>/06-tasks.md`
- `docs/sdd-cycles/<cycle-id>/approvals.md`
