# SDD Stage 06 - Tasks

## Status

Approved for execution (post-HITL closure of PND-PHI-001..006).

## Task List

- **T01 (E3/E5):** Definir schema/config PhiCube
  - `phicube_enabled`
  - `phicube_mode`
  - thresholds globais
  - overrides por `symbol/timeframe`
  - baseline inicial para calibração por `symbol/timeframe` (PND-PHI-001)

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
  - incluir contratos do algoritmo de fronteira fractal `5-3` (PND-PHI-003)

- **T08 (E6):** Testes de integração
  - engine + registry + mode flags

- **T09 (E1/E6):** Rollout faseado com gates
  - shadow -> advisory -> active (canário)

- **T10 (E1):** Evidências finais + aprovação de fechamento

## HITL Decisions Bound to Tasks

- `PND-PHI-001 = B`: thresholds numéricos por `symbol/timeframe`
  - impacta diretamente T01, T06, T07, T08.
- `PND-PHI-003 = B`: algoritmo formal fractal `5-3`
  - impacta diretamente T02, T06, T07, T08.
- `PND-PHI-004 = B`: consolidação composta (tempo + volatilidade + divergência)
  - impacta T02, T06, T07.
- `PND-PHI-005 = B`: ajuste de stop por bandas MIMA/MIMASAR
  - impacta T02, T05, T06.
- `PND-PHI-006 = A`: MIMASAR externo
  - restringe implementação em T02/T03.
- `PND-PHI-002 = A`: `Phi^3` interpretativo
  - restringe implementação em T02/T05 (sem fórmula executável).

## Core Skills Binding

- Execução das tasks deve aplicar skills do core Davi em:
  `agent-davi/templates/davi-orchestrator/core/skills`
- Skills mínimas para esta rodada:
  - `engineering/diagnose`
  - `engineering/tdd`
  - `engineering/grill-with-docs`
  - `engineering/triage`
  - `productivity/caveman`
  - `productivity/grill-me`
  - `productivity/handoff`
  - `productivity/write-a-skill`
  - `misc/git-guardrails-claude-code`
  - `misc/migrate-to-shoehorn`
  - `misc/scaffold-exercises`
  - `misc/setup-pre-commit`
  - `personal/edit-article`
  - `personal/obsidian-vault`

## Dependencies

- T02 depende de T01
- T03 depende de T02
- T04/T05 dependem de T03
- T06 depende de T02
- T07 depende de T04
- T08 depende de T03/T06/T07
- T09 depende de T08
- T10 depende de T09
