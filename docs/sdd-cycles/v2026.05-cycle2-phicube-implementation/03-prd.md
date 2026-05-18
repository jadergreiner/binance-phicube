# SDD Stage 03 - PRD

## Product Goal

Operacionalizar regras PhiCube no `binance-phicube` com decisão explicável,
rollout controlado e governança por gates.

## Users

- Operador/trader
- Engenharia
- Governança/QA

## Functional Requirements

- RF-01: Classificar estado de mercado e expor em PT-BR com explicação humana:
  - `alta_forte`: os sinais apontam subida consistente
  - `baixa_forte`: os sinais apontam queda consistente
  - `consolidacao`: o preço está sem direção clara
  - `transicao`: o mercado está mudando de comportamento
- RF-02: Emitir `SignalResult`/`NullSignalResult` com `reason` e `rule_hits`.
- RF-03: Operar em modos `shadow`, `advisory`, `active`.
- RF-04: Permitir thresholds globais e override por `symbol/timeframe`.
- RF-05: Expor diagnóstico técnico PhiCube na API de símbolo.
- RF-06: Registrar eventos de decisão e bloqueio para RCA.

## Non-Functional Requirements

- RNF-01: Reprodutibilidade para mesma entrada + mesma configuração.
- RNF-02: Backward compatibility com `phicube_enabled=false`.
- RNF-03: Promoção de modo só com gates formais e aprovação humana.
- RNF-04: Cobertura mínima unit/contract/integration.
- RNF-05: Rollback imediato por flag.
- RNF-06: Versionamento/auditoria de regras e thresholds.

## Success Metrics

- Completude de diagnóstico > 99% em `shadow`
- Zero ordens abertas por lógica PhiCube em `shadow`
- Regressão zero em contratos atuais de API/engine

## Impacted Rules

- Núcleo v1: RN-PHI-003..016 e RN-PHI-024
- Gestão faseada: RN-PHI-017..022
- Governança/risco: RN-PHI-023..025

## HITL Decisions (PND-PHI Closure)

| Pending ID | Decision | Effect on PRD |
| --- | --- | --- |
| PND-PHI-001 | B - Numeric thresholds per symbol/timeframe | RF-04 and RNF-06 become mandatory for deterministic operation. |
| PND-PHI-003 | B - Formal algorithm for fractal 5-3 + contract tests | Requires deterministic boundary detection and contract evidence. |
| PND-PHI-004 | B - Composite consolidation rule (time + volatility + divergence) | Consolidation and transition classification must use objective gates. |
| PND-PHI-005 | B - Stop adjustment by MIMA/MIMASAR distance bands | Risk-management behavior must be traceable and testable. |
| PND-PHI-006 | A - MIMASAR as external signal only | No proprietary reverse-engineering in this cycle. |
| PND-PHI-002 | A - Phi^3 as interpretative context only | No executable wave-sizing formula in this cycle baseline. |

## Status

Approved by human.
