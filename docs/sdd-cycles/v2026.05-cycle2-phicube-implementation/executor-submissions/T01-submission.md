# Executor Submission - T01

## Metadata

- Cycle ID: `v2026.05-cycle2-phicube-implementation`
- Task ID: `T01`
- Submitted by: Davi (E1 orchestration)
- Date: 2026-05-17
- Status: Completed

## Task Summary

Definir schema/config PhiCube para ativacao controlada e parametrizacao:

- `phicube_enabled`
- `phicube_mode` (`shadow`, `advisory`, `active`)
- thresholds globais
- overrides por `symbol/timeframe`

## Required Inputs

- `docs/sdd-cycles/v2026.05-cycle2-phicube-implementation/04-specs.md`
- `docs/sdd-cycles/v2026.05-cycle2-phicube-implementation/05-plan.md`
- `docs/sdd-cycles/v2026.05-cycle2-phicube-implementation/06-tasks.md`
- `docs/sdd-cycles/v2026.05-cycle2-phicube-implementation/approvals.md`
- `templates/davi-orchestrator/executors/execution-flow.policy.md`
- `templates/davi-orchestrator/executors/executor-governance.policy.md`
- `templates/davi-orchestrator/execution/executor-task.template.md`

## Skills to Apply (Mandatory)

- `agent-davi/templates/davi-orchestrator/core/skills/engineering/diagnose`
- `agent-davi/templates/davi-orchestrator/core/skills/engineering/tdd`
- `agent-davi/templates/davi-orchestrator/core/skills/engineering/grill-with-docs`
- `agent-davi/templates/davi-orchestrator/core/skills/engineering/triage`
- `agent-davi/templates/davi-orchestrator/core/skills/productivity/caveman`
- `agent-davi/templates/davi-orchestrator/core/skills/productivity/grill-me`
- `agent-davi/templates/davi-orchestrator/core/skills/productivity/handoff`
- `agent-davi/templates/davi-orchestrator/core/skills/productivity/write-a-skill`
- `agent-davi/templates/davi-orchestrator/core/skills/misc/git-guardrails-claude-code`
- `agent-davi/templates/davi-orchestrator/core/skills/misc/migrate-to-shoehorn`
- `agent-davi/templates/davi-orchestrator/core/skills/misc/scaffold-exercises`
- `agent-davi/templates/davi-orchestrator/core/skills/misc/setup-pre-commit`
- `agent-davi/templates/davi-orchestrator/core/skills/personal/edit-article`
- `agent-davi/templates/davi-orchestrator/core/skills/personal/obsidian-vault`

## Executor Routing

1. E1 - Tech Lead

- Abrir lane de execucao de T01 e controlar gates.

1. E2 - Arquiteto de Solucoes

- Revisar desenho do contrato de configuracao e compatibilidade com fluxo atual.

1. E3 - Arquiteto de Dados

- Definir contrato de dados de thresholds e schema de override
  por `symbol/timeframe`.

1. E4 - Engenheiro de ML

- N/A para execucao direta de T01.
- Consultivo apenas se parametros impactarem pipelines de suporte ML.

1. E5 - Engenheiro de Software

- Implementar schema/config e validacoes de entrada conforme contrato aprovado.

1. E6 - QA

- Validar criterio de aceite de T01 e evidencias de configuracao.

## Mandatory Gates

- G1: Entradas aprovadas (SPEC/Plan/Tasks/Approvals)
- G2: Revisoes E2/E3 completas para T01
- G3: Lint gate `PASS` em artefatos alterados
- G4: QA com decisao de aceite para T01
- G5: Aderencia obrigatoria as decisoes HITL (`PND-PHI-001..006`)
- G6: Aplicacao obrigatoria das skills do core Davi registradas nesta submissao

## Acceptance for T01

- Contrato de configuracao PhiCube documentado e implementavel.
- Campos obrigatorios definidos:
  - `phicube_enabled`
  - `phicube_mode`
  - thresholds globais
  - overrides por `symbol/timeframe`
- Regras de validacao para valores invalidos e fallback explicitas.
- Evidencias de validacao registradas.
- Decisoes HITL incorporadas no escopo:
  - `PND-PHI-001 = B`: baseline de thresholds por `symbol/timeframe`
  - `PND-PHI-006 = A`: MIMASAR externo, sem reverse-engineering
  - `PND-PHI-002 = A`: `Phi^3` apenas interpretativo neste ciclo

## Notes

- Esta submissao formaliza a execucao de T01 apos fechamento HITL.

## Execution Evidence

### Changed files

- `src/config/settings.py`
- `tests/config/test_settings.py`

### Schema and validation evidence

- `phicube_enabled` como feature flag global.
- `phicube_mode` com enum estrito: `shadow | advisory | active`.
- `phicube_thresholds_global` com validadores:
  - aceita `dict`/JSON valido;
  - rejeita chave vazia;
  - rejeita valor nao numerico;
  - rejeita valor negativo (`>= 0`).
- `phicube_thresholds_overrides` com validadores:
  - exige formato `SYMBOL:TIMEFRAME`;
  - normaliza chave para `SYMBOL:timeframe`;
  - valida payload de thresholds numericos e nao negativos.
- Fallback deterministico: `get_phicube_thresholds(symbol, timeframe)` aplica
  precedencia `override -> global`.

### Test evidence (QA target)

- Command:
  - `pytest -q tests/config/test_settings.py`
- Result:
  - `18 passed in 0.50s`
- Cobertura de cenarios-chave:
  - defaults PhiCube (`phicube_enabled=false`, `phicube_mode=shadow`);
  - merge de override por `symbol/timeframe`;
  - rejeicao de chave invalida em override;
  - rejeicao de threshold global negativo.
