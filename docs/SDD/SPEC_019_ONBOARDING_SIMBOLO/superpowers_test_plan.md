# Superpowers - Testes

## Matriz Regra -> Teste
| Regra SPEC | Tipo | Caminho do teste | Cenarios | Status |
|---|---|---|---|---|
| Legado síncrono desativado (`410`) | Unitario/API | tests/api/test_onboarding.py | Positivo | implementado |
| Criação e consulta de job assíncrono | Unitario/API | tests/api/test_onboarding.py | Positivo/Borda | existente |
| Frontend sem fallback legado | Regressao UI | tests/dashboard/test_frontend.py | Negativo (rota legada ausente) | implementado |

## Casos Criticos
- Cenario: cliente antigo chama `/onboarding/{symbol}/backtest`
  - Risco: quebra sem orientação
  - Resultado esperado: `410 Gone` com payload de migração

## Comandos de Execucao
```bash
pytest tests/api/test_onboarding.py tests/dashboard/test_frontend.py -q
```

```bash
ruff check src/api/routes/onboarding.py src/frontend/static/app.js tests/api/test_onboarding.py tests/dashboard/test_frontend.py docs/SDD/SPEC_019_ONBOARDING_SIMBOLO/SPEC.md
```

## Evidencias Esperadas
- Tests pass: sim
- Nenhuma regressao no fluxo assíncrono: sim

## Gaps de Cobertura
- Gap: teste e2e contra cliente externo legado
  - Impacto: baixo
  - Plano de fechamento: monitorar logs de `legacy_endpoint_deprecated`
