# Superpowers - Plano

## Escopo
- Em escopo:
  - desativar endpoint legado síncrono `/onboarding/{symbol}/backtest` imediatamente.
  - remover fallback legado no frontend de onboarding.
  - atualizar SPEC_019 e artefatos de governança.
  - validar por testes e lint focados.
- Fora de escopo:
  - novas features de onboarding.
  - rollback automatizado.
- Dependencias:
  - `src/api/routes/onboarding.py`
  - `src/frontend/static/app.js`
  - `tests/api/test_onboarding.py`
  - `tests/dashboard/test_frontend.py`

## Tarefas
| ID | Tarefa | Dono | Status | Bloqueios |
|---|---|---|---|---|
| T1 | Backend legado -> `410 Gone` com migração | codex | done |  |
| T2 | Remover fallback legado no frontend | codex | done |  |
| T3 | Ajustar testes (API/UI) para cenário assíncrono-only | codex | done |  |
| T4 | Atualizar SPEC_019 e status SDD | codex | done |  |
| T5 | Executar pytest + ruff check focados | codex | todo |  |

## Sequenciamento
1. Corte backend.
2. Remoção fallback frontend.
3. Atualização de testes.
4. Sincronização da SPEC e artefatos.
5. Validação final.

## Riscos e Mitigacao
| Risco | Probabilidade | Impacto | Mitigacao |
|---|---|---|---|
| Cliente antigo chamar endpoint legado | Alta | Medio | `410 Gone` com migração explícita |
| Regressão na UI de onboarding | Media | Medio | testes de frontend e fluxo de job |

## Definition of Done (DoD)
- [x] SPEC atualizada antes do codigo
- [ ] Todos os testes planejados executados
- [x] Rastreabilidade regra -> teste -> codigo
- [ ] Review final sem bloqueios P0/P1
