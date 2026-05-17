# SDD Stage 06 - Tasks

## Status

Approved and completed (T01..T10 concluded with formal human closeout approval).

## Task List

- **T01 (E3/E5):** Definir schema/config PhiCube
  - `phicube_enabled`
  - `phicube_mode`
  - thresholds globais
  - overrides por `symbol/timeframe`

- **T02 (E4/E5):** Implementar plugin PhiCube v1
  - RN-PHI-003..016 + RN-PHI-024
  - saída com `rule_hits` + `reason`

- **T03 (E5):** Integrar plugin ao SignalEngine/PluginRegistry
  - sem regressão com `phicube_enabled=false`

- **T04 (E5):** Atualizar API de símbolo
  - `estado_mercado` em PT-BR
  - `explicacao_humana` não técnica

- **T05 (E5/E6):** Instrumentar logs estruturados
  - `estado_mercado`, `explicacao_humana`, `reason`, `rule_hits`, `phicube_mode`

- **T06 (E6):** Testes unitários de classificação e gates

- **T07 (E6):** Testes de contrato para payload de diagnóstico

- **T08 (E6):** Testes de integração
  - engine + registry + mode flags

- **T09 (E1/E6):** Rollout faseado com gates
  - shadow -> advisory -> active (canário)

- **T10 (E1):** Evidências finais + aprovação de fechamento

## Dependencies

- T02 depende de T01
- T03 depende de T02
- T04/T05 dependem de T03
- T06 depende de T02
- T07 depende de T04
- T08 depende de T03/T06/T07
- T09 depende de T08
- T10 depende de T09
