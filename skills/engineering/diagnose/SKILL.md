---
name: diagnose
description: Disciplined diagnosis loop for hard bugs and performance regressions. Reproduce -> minimize -> hypothesize -> instrument -> fix -> regression-test.
reference:
  - https://github.com/mattpocock/skills/tree/main/skills/engineering/diagnose
---

# Skill: Diagnose

## Mission

Run a disciplined RCA loop for hard bugs and regressions with objective
evidence, controlled hypotheses, and explicit closure criteria.

## When to use

- User asks to debug, diagnose, or investigate a difficult bug.
- Failures are intermittent, unclear, or multi-factor.
- Performance regression needs measurement-driven analysis.

## Required inputs

- Problem statement (symptom, expected vs actual behavior).
- Repro context (environment, command path, timeframe).
- Relevant project knowledge (`.davi/project-knowledge/*`, when available).
- Existing CONTEXT/ADR references in the affected area.

## Phase 1 - Build feedback loop (mandatory)

This is the core of the skill. Do not continue without a loop you trust.

Preferred loop construction order:

1. Failing test at a seam that reaches the bug.
1. Scripted API/CLI repro with deterministic pass/fail signal.
1. Replay captured artifact (request, payload, log, trace).
1. Minimal harness that isolates the buggy path.
1. Fuzz/property loop for low-frequency errors.
1. Bisection or differential loop between known states.
1. HITL script only as last resort.

Loop quality goals:

- Fast enough for iteration.
- Deterministic or with sufficiently high repro rate.
- Asserts exact symptom, not generic failure.

If no viable loop is possible:

- Stop and state it explicitly.
- List attempts made.
- Ask human for missing artifact/access/permission.
- Do not move to hypothesis stage.

## Phase 2 - Reproduce

- Run the loop and confirm it reproduces the user-reported failure mode.
- Capture exact symptom evidence (error, wrong output, timing).
- For flaky bugs, raise reproduction rate until debuggable.

## Phase 3 - Hypothesize

- Generate 3-5 ranked and falsifiable hypotheses before testing.
- Each hypothesis must include a prediction:
  - "If X is the cause, changing Y will produce Z."
- Present ranked hypotheses to human for quick re-prioritization.

## Phase 4 - Instrument

- Map each probe to one hypothesis prediction.
- Change one variable at a time.
- Prefer debugger/REPL first, then targeted logs.
- Never do "log everything and grep".
- Tag temporary debug logs with unique prefix (example: `[DEBUG-<id>]`).

Performance branch:

- Establish baseline measurement before changing code.
- Use timing/profiler/query-plan evidence, then bisect if needed.

## Phase 5 - Fix + regression test

- Create regression test before fix only when seam is correct.
- Correct seam means test captures real bug pattern at call site.
- If seam is insufficient, document as architecture finding.

When seam is correct:

1. Turn minimized repro into failing test.
1. Confirm failing state.
1. Apply fix.
1. Confirm passing test.
1. Re-run original feedback loop scenario.

## Phase 6 - Cleanup + post-mortem

Required before closure:

- Original repro no longer reproduces.
- Regression test passes (or missing seam is documented).
- Temporary `[DEBUG-*]` instrumentation removed.
- Throwaway debug artifacts removed or isolated.
- Root cause statement documented with supporting evidence.

## Davi governance gates

- High-impact decisions require explicit human approval.
- If conflict appears with approved RN/RA/RG rules, escalate to refiners.
- If fix implies scope change, pause RCA execution path and return to
  specification/refinement gate.

## Output template

- RCA status: confirmed | not confirmed | blocked
- Symptom and reproducibility summary
- Ranked hypotheses and tested probes
- Confirmed root cause (or reason unresolved)
- Proposed fix and regression-test status
- Residual risks
- Recommended next steps

## Quality rules

- No root-cause claim without evidence.
- No behavior change rollout without gate when impact is critical.
- Prefer minimal and reversible probes.
- Keep investigation log auditable end-to-end.
