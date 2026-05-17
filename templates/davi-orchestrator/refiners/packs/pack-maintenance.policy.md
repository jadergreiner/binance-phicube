# Pack Maintenance Policy

## Ownership Model

Each pack must have:

- `owner` (required)
- `co-owner` (optional)

Default ownership by role (replace with names when desired):

- `business.*` -> Product Owner
- `architecture.*` -> Architecture Owner
- `governance.*` -> Governance Owner

## Review Cadence

No fixed periodic cadence.
Review is event-driven.

## Mandatory Review Triggers

### Business Packs

Any product change must trigger review of current business rules.

### Architecture Packs

Review when a change impacts modules, integrations,
execution flow, or technical constraints.

### Governance Packs

Review when a change impacts risk, controls, policy, compliance, or auditability.

## Pack Evolution Rules

- Create:
  - New recurring knowledge cannot fit existing boundary without ambiguity.
- Split:
  - Single pack is too broad and creates repeated conflicts.
- Merge:
  - Two packs remain overlapping across two consecutive cycles.
- Archive:
  - Launcher/flow is deactivated or obsolete across two consecutive cycles.

## Minimum Quality for Any Update

- Boundary (`in`/`out`) remains explicit.
- Version and changelog updated.
- Decision rationale recorded.
- Links/evidence validated.

## Versioning and Evidence Standard

Primary version format:

- `vYYYY.MM-cycleN` (example: `v2026.05-cycle3`)

Changelog impact tag (mandatory per change):

- `major`: boundary/contract changes with broader impact
- `minor`: additive updates without boundary break
- `patch`: small fixes/clarifications

Evidence block required in each update:

- SDD cycle id
- Related stage approvals
- Affected pack(s)
- Why changed
