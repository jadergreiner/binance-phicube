# SDD Stage 05 - Plan

## Plan Overview

### P1 - Foundation

- Config/flags (`phicube_enabled`, `phicube_mode`, thresholds)
- Contrato de decisão (`rule_hits`, `reason`, `estado_mercado`,
  `explicacao_humana`)
- Owners: E2, E3, E5

### P2 - Decision Core v1

- Plugin PhiCube com RN-PHI-003..016 + RN-PHI-024
- Integração com engine sem regressão
- Owners: E4, E5, E2

### P3 - Operational Diagnostics

- API de símbolo com estado PT-BR + explicação não técnica
- Logs estruturados para RCA
- Owners: E5, E6, E1

### P4 - Controlled Rollout

- `shadow` completo
- `advisory` validado
- `active` canário
- Owners: E1, E6, E2

### P5 - Closure

- Evidências finais
- Checklist de aprovação
- Atualização documental
- Owners: E1, E6

## Critical Sequence

P1 -> P2 -> P3 -> P4 -> P5

## Contingency

Rollback imediato por flag para último modo estável.

## Status

Approved by human.
