# spec_status_update — SPEC_019

## Contexto
- spec_id: SPEC_019
- atualizado_por: time-b-execucao
- data: 2026-05-09

## Resumo de Execucao
- status_geral: concluido
- percentual_estimado: 100
- objetivo: desativação imediata do endpoint legado síncrono de backtest

## Status por Task

| task_id | status | observacao |
|---|---|---|
| T1 | done | Endpoint legado `/onboarding/{symbol}/backtest` retorna `410 Gone`. |
| T2 | done | Fallback legado removido do frontend onboarding. |
| T3 | done | Testes ajustados para contrato assíncrono-only. |
| T4 | done | SPEC_019 atualizada sem compatibilidade transitória. |
| T5 | done | `pytest` e `ruff check` aprovados. |

## Evidencias
- `pytest tests/api/test_onboarding.py tests/dashboard/test_frontend.py -q` -> `39 passed`
- `ruff check src/api/routes/onboarding.py tests/api/test_onboarding.py tests/dashboard/test_frontend.py` -> `ok`

## Desvios de SPEC
- nenhum

## Bloqueios
- nenhum

## Proximos Passos
1. Monitorar logs de uso legado pós-release para identificação de clientes antigos.
