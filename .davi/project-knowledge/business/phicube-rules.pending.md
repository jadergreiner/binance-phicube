# PhiCube Rules - Pending Human Decisions

## Purpose

Register ambiguities from PDF parsing that require human approval before turning
rules into deterministic execution logic.

## Decisions (Human-in-the-Loop)

| Pending ID | Topic | Final Decision | Status | Artifacts Impacted |
| --- | --- | --- | --- | --- |
| PND-PHI-001 | Exact thresholds for MIMA_ROC and SANTO strength | **B** - Define numeric thresholds per symbol/timeframe. | Closed | `SPEC`, `tasks`, `contract tests`, `signal explanation` |
| PND-PHI-003 | Deterministic wave boundary detection for fractal 5-3 | **B** - Formal algorithm and contract tests. | Closed | `SPEC`, `tasks`, `strategy`, `contract tests` |
| PND-PHI-004 | Consolidation duration threshold | **B** - Composite threshold (time + volatility + divergence). | Closed | `SPEC`, `tasks`, `no-signal logic`, `risk status` |
| PND-PHI-005 | Stop adjustment formula | **B** - MIMA/MIMASAR distance bands. | Closed | `SPEC`, `tasks`, `risk management`, `trade management` |
| PND-PHI-006 | MIMASAR computation internals | **A** - Treat as external signal only (no proprietary reverse-engineering). | Closed | `SPEC`, `governance`, `integration contracts` |
| PND-PHI-002 | Objective formula for wave sizing with `Phi^3` | **A** - Interpretative context only in this cycle (no executable sizing formula yet). | Closed | `SPEC`, `knowledge pack`, `future backlog` |

## Closure Summary

- All pending decisions `PND-PHI-001..006` were formally approved by the human.
- Deterministic implementation can proceed for the approved scope.
- Items intentionally kept non-formulaic in this cycle:
  - `PND-PHI-002` (`Phi^3` as interpretative context)
  - `PND-PHI-006` (MIMASAR treated as external signal)

## Blocking Policy

- Original pendings are closed for this decision round.
- New ambiguities, if any, must be registered as `PND-PHI-00X` before
  implementation changes.
