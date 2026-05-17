# Refinement Flow Checklist

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
