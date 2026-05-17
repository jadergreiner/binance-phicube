# Davi Intake Paths Policy

## Path A: Q&A

### Use when (Q&A)

- User asks for explanation, status, or clarification.
- No immediate product change is requested.

### Mandatory output (Q&A)

- Direct answer.
- References to canonical shared packs and relevant consulted artifacts.

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

## Shared Gates for RCA and New Implementation

- Human approval per SDD stage is mandatory.
- All artifacts must be persisted.
- No Executor handoff without approved SPEC and approved Tasks.
- No progression while artifact lint gate is `FAIL`.

## Global Prerequisite

- Knowledge Gate must run before selecting any path.
