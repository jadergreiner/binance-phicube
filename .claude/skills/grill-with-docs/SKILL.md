---
name: grill-with-docs
description: >
  This skill should be used when the user asks to "validate a plan against the
  docs", "check alignment with the spec", "grill with docs", "alinhar com
  contexto", "revisar contra ADR", "validar plano com documentação", "confrontar
  proposta com regras", or needs to verify that a proposal, plan, or technical
  decision is consistent with approved rules (RN/RA/RG), ADRs, CONTEXT.md, or
  domain knowledge packs before implementation begins. Also activate when the user
  says "use grill-with-docs" or describes a risk of misalignment between what was
  designed and what was approved. Apply before any architecture change, critical
  flow, or new API — do not skip when the stakes of getting it wrong are high.
version: 1.0.0
---

# Skill: Grill With Docs

Validate a proposal's robustness against the project's documentary model.
Eliminate terminological ambiguity and record decisions traceably before or
during specification — never after the fact.

No implementation code is written during this skill.

## When this skill applies

- Before a significant implementation (architecture change, critical flow, API).
- When there is risk of misalignment between the proposal and existing approved
  decisions.
- When the user requests rigorous validation of a plan, language, or assumptions.

## Minimum inputs required

- **Proposal/plan**: PRD, SPEC, technical plan, or task list.
- **Reference sources** for the domain:
  - `CONTEXT.md` (when it exists)
  - ADRs and architectural docs
  - Approved RN/RA/RG rules
  - Project knowledge packs (when applicable)
- **Scope boundaries and success criteria**.

## Execution protocol

### Step 1 — Collect doc baseline

List and read only the documents relevant to the proposal. Identify the
version/state of each source (current, legacy, superseded).

### Step 2 — Extract domain assertions

Extract normative statements from the sources:

- Invariants
- Canonical terms
- Operational constraints
- Active architectural decisions

Mark explicit conflicts between sources.

### Step 3 — Stress the proposal

Compare the proposal item by item against the extracted assertions. Classify
each item as:

- `adherent` — consistent with approved docs
- `divergent` — conflicts with a documented decision
- `unknown` — no coverage in the docs

For each divergence, generate a trade-off analysis by dimension: business,
architecture, governance.

### Step 4 — Human decision gate (mandatory)

Present divergences and decision options to the user. Do not advance to
execution while critical divergences remain open. If necessary, propose a
rule/document evolution before proceeding.

### Step 5 — Update docs from approved decisions

Apply only formally approved decisions. Update:

- `CONTEXT.md` (when applicable)
- Affected ADR(s)
- Cross-reference in the current SDD artifact

Ensure traceability: what changed, why, which decision approved it.

### Step 6 — Closeout

Emit a final summary with: adherences, resolved divergences, remaining
open items. Declare readiness for the next gate (Refiner/Executor).

## Governance gates (Davi project)

- Divergence with approved RN/RA/RG requires a formal human decision.
- Scope change must return to the SDD refinement flow.
- Without a formal decision, status must remain `blocked`.

## Required output format

```
GRILL STATUS: ready | blocked

DOCS ANALYZED
  - doc: path or name | state: current/legacy/superseded

ADHERENCE MAP
  Item 1: adherent — reason
  Item 2: divergent — conflict with [ADR-X]: ...
  Item 3: unknown — no coverage found

HUMAN DECISIONS RECORDED
  Decision 1: ...

DOCUMENTARY UPDATES APPLIED
  - file: ... | change: ...

RESIDUAL RISKS
  ...

NEXT STEP
  ...
```

## Quality rules

- No implementation code during this skill.
- No silent rule or document changes.
- Every documentary change must point to an approved decision.
- Terminology must remain consistent with the canonical context.
