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

## Status

Approved by human.
