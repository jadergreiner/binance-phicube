# Executor Submission - T08

## Metadata

- Cycle ID: `v2026.05-cycle2-phicube-implementation`
- Task ID: `T08`
- Submitted by: Davi (E1 orchestration)
- Date: 2026-05-17
- Status: Completed (awaiting formal human approval)

## Task Summary

Executar testes de integração entre:

- engine
- registry
- mode flags (`phicube_enabled`, `phicube_mode`)

## Required Inputs

- `docs/sdd-cycles/v2026.05-cycle2-phicube-implementation/04-specs.md`
- `docs/sdd-cycles/v2026.05-cycle2-phicube-implementation/05-plan.md`
- `docs/sdd-cycles/v2026.05-cycle2-phicube-implementation/06-tasks.md`
- `docs/sdd-cycles/v2026.05-cycle2-phicube-implementation/approvals.md`
- `docs/sdd-cycles/v2026.05-cycle2-phicube-implementation/executor-submissions/T03-submission.md`
- `docs/sdd-cycles/v2026.05-cycle2-phicube-implementation/executor-submissions/T05-submission.md`

## Executor Routing

1. E1 - Tech Lead

- Orquestração de cobertura integrada para T08.

1. E2 - Arquiteto de Soluções

- Revisão da cadeia de roteamento de plugin no `SignalEngine`.

1. E3 - Arquiteto de Dados

- Revisão de propagação de `phicube_mode` no payload de diagnóstico.

1. E4 - Engenheiro de ML

- N/A para este recorte de integração.

1. E5 - Engenheiro de Software

- Implementação dos cenários de integração em testes.

1. E6 - QA

- Execução e validação dos cenários integrados.

## Mandatory Gates

- G1: Entradas aprovadas (SPEC/Plan/Tasks/Approvals)
- G2: Revisões E2/E3 completas para T08
- G3: Lint gate `PASS` em artefatos alterados
- G4: QA com decisão de aceite para T08

## Acceptance for T08

- Cadeia `SignalEngine` usa somente `williams` quando `phicube_enabled=false`.
- Cadeia `SignalEngine` usa `phicube -> williams` quando `phicube_enabled=true`.
- `phicube_mode` propagado no `signal_cycle_diagnostic`.

## Execution Evidence

### Changed files

- `tests/test_runtime_monitor_registry.py`
- `tests/trading/test_trading_monitor_signal_outcomes.py`

### Integration scenarios added

- `RuntimeMonitorRegistry._make_signal_engine()`:
  - com flag desabilitada: chain `["williams"]`
  - com flag habilitada: chain `["phicube", "williams"]`
- `TradingMonitor._tick()`:
  - valida persistência de `phicube_mode="advisory"` no diagnóstico.

### Gate evidence

- G3 Lint:
  - `ruff check tests/test_runtime_monitor_registry.py tests/trading/test_trading_monitor_signal_outcomes.py` -> PASS
  - `ruff format --check tests/test_runtime_monitor_registry.py tests/trading/test_trading_monitor_signal_outcomes.py` -> PASS
- G4 QA (targeted integration tests):
  - `pytest -q tests/test_runtime_monitor_registry.py tests/trading/test_trading_monitor_signal_outcomes.py` -> `14 passed`
