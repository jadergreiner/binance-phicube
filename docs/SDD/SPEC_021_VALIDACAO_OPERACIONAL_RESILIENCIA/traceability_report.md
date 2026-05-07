# Traceability Report - SPEC_021

## Objetivo

Consolidar rastreabilidade objetiva entre PRD, SPEC, testes e evidencias operacionais da SPEC_021.

## Mapa PRD -> SPEC_021 -> Testes/Evidencias

| PRD / KR | SPEC_021 item | Evidencia |
|---|---|---|
| Cobertura de testes >= 80% | task_003 - quality gate | `reports/spec021_quality_gate.json` (`status=pass`, total 81%, risk_manager 100%) |
| Seguranca operacional e hardening | task_004 - hardening checklist | `reports/spec021_hardening_report.json` (`status=pass`) |
| Rastreabilidade tecnica do core (Signal/Risk/Order) | task_002 - compliance matrix | `docs/SDD/SPEC_021_VALIDACAO_OPERACIONAL_RESILIENCIA/compliance_matrix.md` |
| Rollback de ordens em falha de protecao (SL/TP) | task_002 - REQ-ORD-002 | `tests/trading/test_order_manager.py` (assert de `cancel_all_orders` em falha de SL e TP) |
| Resiliencia continua validada | task_001 + task_005 - soak 48h | `soak_protocol.md`, `soak_evidence.template.json`, `evidence/soak_evidence_pending.json` |

## Estado Atual

- task_001: concluida
- task_002: concluida
- task_003: concluida
- task_004: concluida
- task_005: em progresso (bloqueada por execucao real de 48h)

## Gap Remanescente para Fechamento da SPEC

1. Executar janela operacional real de 48h.
2. Gerar `soak_evidence.json` final com `duration_hours >= 48` e `result=approved`.
3. Validar evidencia final com script automatizado da SPEC_021.
4. Atualizar status para `Concluida` sem inferencia.
