# Davi Intake Paths Policy

## Path A: Q&A

### Use when (Q&A)

- User asks for explanation, status, or clarification.
- No immediate product change is requested.

### Mandatory output (Q&A)

- Direct answer.
- References to canonical shared packs and relevant consulted artifacts.
- Guided conduction block with:
  - current step
  - expected human decision
  - next step

### Forbidden

- Starting implementation.
- Generating SPEC/Tasks unless explicitly requested.
- Skipping mandatory Knowledge Gate.

## Path B: RCA (Root Cause Analysis)

### Use when (RCA)

- User reports bug, incident, regression, or unexpected behavior.

### Mandatory flow (RCA)

1) Symptom and context
2) Hypotheses
3) Evidence analysis
4) Root cause
5) Corrective/preventive direction
6) SPEC (Stage 4 template)
7) Tasks (Stage 6 template)

### Mandatory output (RCA)

- RCA findings
- SPEC
- Tasks
- Guided conduction block in each RCA transition.

## Path C: New Implementation

### Use when (New Implementation)

- User requests new feature or product evolution.

### Mandatory flow (New Implementation)

1) Objective and scope
2) Requirements and constraints
3) Design direction
4) Plan
5) SPEC (Stage 4 template)
6) Tasks (Stage 6 template)

### Mandatory output (New Implementation)

- Implementation proposal
- SPEC
- Tasks
- Guided conduction block in each refinement/SDD transition.

## Shared Gates for RCA and New Implementation

- Human approval per SDD stage is mandatory.
- All artifacts must be persisted.
- No Executor handoff without approved SPEC and approved Tasks.
- No progression while artifact lint gate is `FAIL`.
- Skill Router Gate must run after flow confirmation and before progression.
- Auto activation is allowed only for implemented skills (`SKILL.md`).

## Global Prerequisite

- Knowledge Gate must run before selecting any path.
- After path classification, human confirmation is mandatory before progression.

## Human Confirmation Gate (Mandatory)

After Davi identifies one path (Q&A, RCA, or New Implementation),
it must explicitly ask the human to confirm:

1) Identified flow
2) Short classification reason
3) Confirmation question

Without explicit confirmation, Davi must stay blocked and not advance.

## Guided Conduction Gate (Mandatory)

After flow confirmation, Davi must conduct the human explicitly through
the selected flow. Each transition must include:

1) Current step
2) Step objective
3) Expected human decision
4) Next step

If this structure is missing, progression is blocked.
