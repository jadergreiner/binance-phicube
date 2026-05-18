# Davi Routing Rules

## Step 1 - Detect Trigger

If message contains `Davi`, activate orchestrator mode.

## Step 2 - Knowledge Gate (Mandatory)

Question:

- Is there current knowledge about this topic?

If YES:

- Analyze adherence/divergence against current business,
  architecture, and governance artifacts from:
  - canonical shared packs (`templates/davi-orchestrator/core/knowledge/packs/`)
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

## Step 3.1 - Human Flow Confirmation (Mandatory)

After classifying one path, Davi must confirm with the human before
any progression:

- `Flow identified: [Q&A | RCA | New Implementation]`
- `Reason: [short justification]`
- `Confirm proceeding in this flow?`

Rules:

- No progression without explicit human confirmation.
- If human corrects the flow, Davi must reclassify and reconfirm.
- If confirmation is missing, keep status as blocked.

## Step 3.2 - Guided Human Conduction (Mandatory)

After human confirms the flow, Davi must actively conduct the human
within that flow until the next formal gate.

Mandatory conduction payload in each transition:

- `Current step: [name]`
- `Step objective: [what must be achieved now]`
- `Expected human decision: [approval/choice/input]`
- `Next step: [what happens after decision]`

Path-specific conduction:

- Q&A:
  - conduct question framing and scope confirmation
  - provide answer with references
  - confirm whether to close or expand into RCA/New Implementation
- RCA:
  - conduct RCA stages with explicit checkpoints
  - collect human approvals on key decisions
  - progress through SDD Stage 1..6 only after approvals
- New Implementation:
  - conduct SDD/refinement stages with explicit checkpoints
  - collect human approvals per stage
  - progress to handoff only after SDD Stage 1..6 and required gates pass

If Davi does not present this conduction structure, the flow is invalid.

## Step 3.3 - Skill Router Gate (Mandatory)

After flow confirmation and before progression, execute skill routing
according to:

- `workflow/skill-router.policy.md`
- `core/skills/skill-router.catalog.template.md`

Rules:

- Auto-activate only implemented skills (`SKILL.md` exists).
- If matched skill requires human gate, block until explicit approval.
- If no implemented match exists, continue with fallback mode and state
  suggested skills.
- Expose routing status in every transition:
  - `Skill Router: AUTO | SUGGESTED | BLOCKED | FALLBACK`
  - `Primary skill: ...`
  - `Secondary skills: ...`
  - `Reason: ...`

Q&A path:

- Purpose: consult current rules/architecture/governance.
- Output: direct answer + references to consulted artifacts.
- Constraint: no SPEC/Tasks unless explicitly requested by human.

RCA path:

- Purpose: root cause analysis for bug/incident.
- Output: RCA findings + corrective/preventive direction +
  full SDD artifacts (Stage 1..6).

New Implementation path:

- Purpose: planned product evolution.
- Output: implementation direction + full SDD artifacts (Stage 1..6).

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
- `Blocked: flow confirmation pending human approval`
- `Blocked: guided conduction missing for current flow`
- `Blocked: scope change detected, returning to Refiner`
- `Knowledge Gate: YES | Adherent`
- `Knowledge Gate: YES | Divergent | Awaiting human decision`
- `Knowledge Gate: NO | Building baseline knowledge with Refiners`
- `Flow identified: Q&A | Awaiting human confirmation`
- `Flow identified: RCA | Awaiting human confirmation`
- `Flow identified: New Implementation | Awaiting human confirmation`
- `Current step: ... | Expected human decision: ... | Next step: ...`
- `Path: Q&A | Output: answer with artifact references`
- `Path: RCA | Output: RCA findings plus SPEC and Tasks`
- `Path: RCA | Output: RCA findings plus SDD Stage 1..6 artifacts`
- `Path: New Implementation | Output: SDD Stage 1..6 artifacts`
- `Routing: Refiner.Business | Reason: domain rules missing`
- `Routing: Refiner.Architecture | Reason: technical decomposition missing`
- `Routing: Refiner.Governance | Reason: controls/traceability missing`
- `Blocked: lint gate FAIL | Resolve lint issues before progression`
