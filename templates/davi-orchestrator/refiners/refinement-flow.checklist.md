# Refinement Flow Checklist

## Mandatory SDD Completion (Refiners)

- [ ] Stage 1 artifact persisted (`01-high-level.md`).
- [ ] Stage 2 artifact persisted (`02-standardized-task.md`).
- [ ] Stage 3 artifact persisted (`03-prd.md`).
- [ ] Stage 4 artifact persisted (`04-specs.md`).
- [ ] Stage 5 artifact persisted (`05-plan.md`).
- [ ] Stage 6 artifact persisted (`06-tasks.md`).
- [ ] Formal human approval recorded for each stage transition.
- [ ] No Executor handoff attempted before all items above are complete.

## Gate 1: Business Rules -> Architecture

- [ ] Problem and expected value are explicit.
- [ ] Domain rules and constraints are explicit.
- [ ] In-scope and out-of-scope are explicit.
- [ ] Acceptance intent is measurable.

## Gate 2: Architecture -> Governance

- [ ] Technical approach is explicit and coherent.
- [ ] Components/modules impacted are listed.
- [ ] Implementation slices/tasks are concrete.
- [ ] Trade-offs and alternatives are documented.

## Gate 3: Governance -> Executor Handoff

- [ ] Policies and compliance checks are listed.
- [ ] Risk controls and rollback intent are explicit.
- [ ] Decision log is complete and traceable.
- [ ] Final refiner spec is approved by human.

## Rework Rules

- Failed Gate 1 returns to Business Rules.
- Failed Gate 2 returns to Architecture.
- Failed Gate 3 returns to Governance.
- Any scope change returns to Business Rules.
