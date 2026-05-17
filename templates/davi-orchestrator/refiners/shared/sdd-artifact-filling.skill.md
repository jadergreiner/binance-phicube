# Shared Skill: sdd-artifact-filling

## Type

Cross-layer shared skill (Business, Architecture, Governance).

## Mission

Ensure SDD artifacts are consistently filled and normalized across the 6 stages.

## Inputs

- Current stage template (`sdd/stages/*.template.md`)
- Previous approved stage artifacts
- Active cycle id

## Outputs

- Completed stage artifact
- Consistency notes vs prior stage
- Approval-ready handoff section

## Rules

- Must preserve stage intent and scope.
- Must not introduce implementation/code actions.
- Must map key decisions to approval records.
- Stage 4 (SPEC) must follow `sdd/stages/04-specs.template.md`
  without removing required sections.
- Must trigger `artifact-lint-gate` after create/edit operations.

## Quality Checklist

- Stage fields complete
- Scope consistent with prior stage
- No unresolved critical ambiguity
- Approval gate section ready
