# Canonical Pack Knowledge - architecture.iniciar

## Status

Canonical shared knowledge (project-applied) near Davi specification.

## Current Technical Mapping

- Deterministic launcher:
  - `agente_autonomo/INICIAR.BAT`
  - Commodity flags exist (`--autotrade-xbrusd`, `--autotrade-xngusd`,
    `--autotrade-xtiusd`, `--autotrade-xauusd`).
- RL launcher:
  - `agente_autonomo/INICIAR_RL.BAT`
  - Current wave includes `XBRUSD`, `XNGUSD`, `XTIUSD`.

## Architectural Risk

- Risk of inconsistency between:
  - official enabled/disabled commodity rule
  - executable launcher paths

## Architectural Rule

- A single validation point must enforce commodity enable/disable status.
- Validation failure must be fail-closed before real execution.

## Traceability

- Cycle id: `v2026.05-cycle1-commodities-toggle`
- Origin evidence:
  - `docs/sdd-cycles/v2026.05-cycle1-commodities-toggle/packs/architecture.iniciar.knowledge.md`
