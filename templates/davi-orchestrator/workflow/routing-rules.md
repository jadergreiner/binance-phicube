# Davi Routing Rules

## Step 1 - Detect Trigger

If message contains `Davi`, activate orchestrator mode.

## Step 2 - Knowledge Gate (Mandatory)

Question:

- Is there current knowledge about this topic?

If YES:

- Analyze adherence/divergence against current business,
  architecture, and governance artifacts from:
  - canonical shared packs (`templates/davi-orchestrator/knowledge/packs/`)
  - project-specific packs (`.davi/project-knowledge/`)
- If divergent:
  - Escalate to human decision with two options:
    1) evolve rules/knowledge
    2) adjust proposal
  - Block path progression until formal human decision.

If NO:

- Route to Refiners to build and register baseline knowledge.
- Ask human approval to promote captured knowledge into shared packs.
- Persist promoted knowledge in canonical packs before progressing.
- Keep SDD cycle artifacts as evidence trail.
- First operational response must follow `workflow/knowledge-gate.response-templates.md`.

## Step 3 - Classify Request

First classify path:

- Q&A
- RCA
- New Implementation

Q&A path:

- Purpose: consult current rules/architecture/governance.
- Output: direct answer + references to consulted artifacts.
- Constraint: no SPEC/Tasks unless explicitly requested by human.

RCA path:

- Purpose: root cause analysis for bug/incident.
- Output: RCA findings + corrective/preventive direction + SPEC + Tasks.

New Implementation path:

- Purpose: planned product evolution.
- Output: implementation direction + SPEC + Tasks.

Route to Refiner when (RCA/New Implementation):

- The request is new or ambiguous.
- Scope, constraints, or acceptance are missing.
- User requests planning/specification.

Within Refiner, route in strict sequence:

1) Business Rules
2) Architecture
3) Governance

Route to Executor when:

- There is an approved refiner spec.
- Tasks and acceptance criteria are explicit.

## Step 4 - Enforce Gate

Before Executor starts, require:

- Link/path to approved spec
- Link/path to approved tasks
- Completed handoff checklist
- Explicit go-ahead to implement
- `refiners/refinement-flow.checklist.md` completed with all gates passed
- `sdd/stage-approval.checklist.md` completed with all six stages approved
- Artifact lint gate status `PASS` for changed artifacts
  (`workflow/artifact-lint-gate.policy.md`)

## Standard Status Messages

- `Routing: Refiner | Reason: missing approved spec`
- `Routing: Executor | Reason: approved spec and gates passed`
- `Blocked: scope change detected, returning to Refiner`
- `Knowledge Gate: YES | Adherent`
- `Knowledge Gate: YES | Divergent | Awaiting human decision`
- `Knowledge Gate: NO | Building baseline knowledge with Refiners`
- `Path: Q&A | Output: answer with artifact references`
- `Path: RCA | Output: RCA findings plus SPEC and Tasks`
- `Path: New Implementation | Output: SPEC and Tasks`
- `Routing: Refiner.Business | Reason: domain rules missing`
- `Routing: Refiner.Architecture | Reason: technical decomposition missing`
- `Routing: Refiner.Governance | Reason: controls/traceability missing`
- `Blocked: lint gate FAIL | Resolve lint issues before progression`
