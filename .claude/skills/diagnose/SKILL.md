---
name: diagnose
description: >
  This skill should be used when the user asks to "diagnose a bug", "run RCA",
  "find the root cause", "debug this", "investigate a regression", "why is this
  failing", "trace the cause", "perform root cause analysis", or describes an
  intermittent failure, a multi-factor bug, or a performance regression with no
  obvious cause. Also activate when the user says "use diagnose", "rodar RCA",
  "analisar causa raiz", "bug intermitente", or "regressao". This skill enforces
  a disciplined reproduce→hypothesize→instrument→fix loop and must be used
  instead of ad-hoc guessing whenever the failure cause is not immediately
  evident from reading the code.
version: 1.0.0
---

# Skill: Diagnose

Execute RCA (Root Cause Analysis) with objective evidence and an auditable
trail. Never propose a fix by assumption — every claim of root cause requires
a concrete, reproducible signal first.

## When this skill applies

- Explicit request for RCA, deep debug, diagnosis, or regression investigation.
- Intermittent, multi-factor, or causally opaque failure.
- Performance regression requiring baseline comparison.
- Any failure where the cause is not immediately visible in the code.

## Minimum inputs required

Before starting, confirm these are available — block if any are missing:

- **Symptom**: observed behavior vs. expected behavior (concrete, not vague).
- **Reproduction context**: environment, command, temporal window.
- **Artifacts**: logs, traces, payloads, screenshots, failing tests.
- **Active rules**: relevant RN/RA/RG business rules when the failure has
  business impact.

If a required input is missing, ask for it explicitly and do not proceed.

## Execution protocol

### Step 1 — Build a feedback loop (mandatory before any hypothesis)

Create a reproducible loop first. Preferred order:

1. Failing test at the correct seam
2. Deterministic API/CLI repro script
3. Replay of a captured artifact
4. Minimal isolated harness
5. Fuzz/property test for rare failures
6. Bisection/diff between states
7. HITL script (last resort only)

If no viable loop can be constructed, **block the RCA** and ask the user for
the missing input. Do not hypothesize without a loop.

### Step 2 — Reproduce

Run the loop and confirm the exact failure mode reported. Record concrete
evidence: error message, incorrect output, latency measurement, reproduction
rate. If reproduction fails, revisit the symptom description with the user.

### Step 3 — Hypothesize

Generate 3–5 falsifiable hypotheses, ranked by likelihood. Each hypothesis
must include a testable prediction:

> "If X is the cause, changing Y will produce Z."

No hypothesis without a prediction. No prediction without a planned probe.

### Step 4 — Instrument

Map each probe to one hypothesis. Change one variable per probe. Prefer
debugger/REPL and surgical log additions. Prefix any temporary log with a
unique tag (e.g., `[DEBUG-RCA-01]`) to make cleanup unambiguous.

Prohibited: "log everything and grep". Each probe must be targeted.

### Step 5 — Fix and add regression test

When the seam is correct:

1. Convert the minimized repro into a failing test.
2. Confirm the test fails.
3. Apply the fix.
4. Confirm the test passes.
5. Re-run the original scenario end-to-end.

If the seam is architecturally wrong, record this as an architectural finding
and escalate — do not patch at the wrong layer.

### Step 6 — Cleanup and close

- Remove all temporary instrumentation.
- Confirm the original repro no longer occurs.
- Confirm the regression is covered by a test, or explicitly document why the
  gap is acceptable.

## Governance gates (Davi project)

- High-impact decisions require human approval before rollout.
- Conflicts with approved RN/RA/RG rules must return to the refiners, not be
  resolved unilaterally.
- Any change that expands scope ends the RCA trail and returns to the
  specification gate.

## Required output format

Produce a structured RCA report with these sections:

```
RCA STATUS: confirmed | not confirmed | blocked

SYMPTOM
  Observed: ...
  Expected: ...
  Reproduction rate: ...

FEEDBACK LOOP
  Method: ...
  Evidence: ...

HYPOTHESES (ranked)
  1. [most likely] — prediction: ...
  2. ...

PROBES EXECUTED
  Probe 1 → hypothesis 1 → result: ...

ROOT CAUSE
  Confirmed: ... (or: blocked because ...)

FIX
  Applied: yes/no
  Regression test: added/gap/N/A

RISKS AND NEXT STEPS
  ...
```

## Quality rules

- No root cause claim without concrete evidence from the feedback loop.
- No critical change rollout without a gate.
- All probes must be minimal, reversible, and auditable.
- Temporary instrumentation must be tagged and removed before closure.
