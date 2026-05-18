# Skill Router Policy

## Purpose

Define how consumer projects automatically activate Davi core skills during
Q&A, RCA, and New Implementation flows.

## Activation model

Skill routing is mandatory after flow confirmation and before progression:

1. Detect current path (`Q&A`, `RCA`, `New Implementation`).
2. Match request signals against skill triggers.
3. Select implemented skills by priority.
4. Apply human gate if impact is high.
5. Execute selected skills or fallback when not implemented.

## Selection rules

- Use only skills that have `SKILL.md` implemented.
- Ignore scaffold-only folders (README-only) for auto execution.
- Prefer one primary skill plus up to two secondary skills.
- If two skills conflict, prefer the one with higher risk-control coverage.

## Human gate rules

Require explicit human approval before auto execution when:

- Scope changes are implied.
- Governance/risk rules may be affected.
- RCA conclusion is not evidence-backed.
- Architectural trade-off is hard to reverse.

Without approval in these cases, mark routing as blocked.

## Fallback behavior

When no implemented skill matches:

- Continue with base Davi flow.
- Emit a structured note:
  - candidate skill(s)
  - reason auto activation was skipped
  - recommendation to implement missing skill

## Consumer extensibility

Consumers may define local trigger overrides in:

- `.davi/skill-router.overrides.yaml`

Rules:

- Local overrides cannot disable mandatory governance gates.
- Local overrides cannot bypass human approval requirements.
- Local overrides can add domain-specific trigger keywords.

## Mandatory status message

Every routed transition must expose:

- `Skill Router: [AUTO | SUGGESTED | BLOCKED | FALLBACK]`
- `Primary skill: [skill-id or none]`
- `Secondary skills: [list or none]`
- `Reason: [short reason]`
