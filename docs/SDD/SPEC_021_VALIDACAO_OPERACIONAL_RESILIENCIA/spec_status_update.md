# spec_status_update - SPEC_021

## Contexto

- spec_id: SPEC_021
- atualizado_por: time-b-execucao
- data: 2026-05-07

## Resumo de Execucao

- status_geral: em_execucao
- percentual_estimado: 96

## Status por Task

| task_id | status | observacao |
|---|---|---|
| task_001 | done | Protocolo de soak 48h e template de evidencia formalizados. |
| task_002 | done | Matriz PRD->SPEC->teste criada para Signal/Risk/Order; lacuna de rollback de ordens (REQ-ORD-002) foi fechada com teste dedicado. |
| task_003 | done | Baseline de cobertura e quality gate implementados com script e contrato de saida JSON; execucao atual aprovada com threshold atendido. |
| task_004 | done | Checklist de hardening criado com validacoes automatizaveis e evidencias manuais requeridas. |
| task_005 | in_progress | Pipeline CI entregue e gates aprovados; rastreabilidade consolidada e validador de soak adicionado; fechamento bloqueado apenas pela execucao real do soak 48h. |

## Evidencias

- soak_protocol: `docs/SDD/SPEC_021_VALIDACAO_OPERACIONAL_RESILIENCIA/soak_protocol.md`
- soak_template: `docs/SDD/SPEC_021_VALIDACAO_OPERACIONAL_RESILIENCIA/soak_evidence.template.json`
- compliance_matrix: `docs/SDD/SPEC_021_VALIDACAO_OPERACIONAL_RESILIENCIA/compliance_matrix.md`
- quality_gate_doc: `docs/SDD/SPEC_021_VALIDACAO_OPERACIONAL_RESILIENCIA/quality_gate.md`
- hardening_doc: `docs/SDD/SPEC_021_VALIDACAO_OPERACIONAL_RESILIENCIA/hardening_checklist.md`
- scripts: `scripts/spec_021/check_quality_gate.py`, `scripts/spec_021/check_hardening.py`, `scripts/spec_021/validate_spec021_artifacts.py`
- ci_workflow: `.github/workflows/spec021-validation.yml`
- artifacts locais: `reports/spec021_quality_gate.json`, `reports/spec021_hardening_report.json`, `reports/coverage.json`
- risk_tests: `tests/trading/test_risk_manager.py`
- order_rollback_tests: `tests/trading/test_order_manager.py`
- soak_pending: `docs/SDD/SPEC_021_VALIDACAO_OPERACIONAL_RESILIENCIA/evidence/soak_evidence_pending.json`
- traceability_report: `docs/SDD/SPEC_021_VALIDACAO_OPERACIONAL_RESILIENCIA/traceability_report.md`
- soak_validator: `scripts/spec_021/validate_soak_evidence.py`

## Desvios de SPEC

- Nenhum desvio de escopo nesta rodada.

## Bloqueios

- Fechamento da task_005 depende de execucao operacional real do soak de 48h e anexacao da evidencia final em `evidence/`.
- Validacao automatizada de soak reprova enquanto `evidence/soak_evidence.json` nao existir com contrato completo.

## Proximos Passos

1. Executar janela operacional real de 48h conforme `soak_protocol.md`.
2. Registrar `soak_evidence.json` final com `result=approved` em `evidence/`.
3. Executar `python scripts/spec_021/validate_soak_evidence.py` e anexar saida.
4. Atualizar `task_005` para `done` e mover SPEC_021 para `Concluida`.
