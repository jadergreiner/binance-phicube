# Plan — SPEC_020

## Meta

- spec_id: SPEC_020
- objetivo: Endurecer governanca SDD, proteger endpoints sensiveis e consolidar fechamento operacional do onboarding.
- escopo: Normalizacao de status (SPEC_013/015/016/017/018/019), autenticacao minima em escrita, fechamento operacional onboarding.
- fora_de_escopo: RBAC completo, multi-estrategia e replatform de dashboard.

## Entradas

- docs/SDD/SPEC_020_HARDENING_GOVERNANCA_SEGURANCA_ONBOARDING/SPEC.md
- PRD.md
- docs/SDD/README.md
- contracts/task.json

## Premissas

- Endpoints de leitura devem manter compatibilidade.
- Ambiente local permite controle de acesso simplificado por token/segredo.
- Evidencias de SPECs anteriores sao recuperaveis no repositorio.

## Riscos e Mitigacoes

| risco | impacto | mitigacao |
|---|---|---|
| Politica de acesso bloquear fluxo legitimo | alto | contrato objetivo + testes positivos/negativos + rollout com flag |
| Falta de evidencias para fechamento retroativo | medio | registrar limitacoes de evidencia no status update com justificativa |
| Regressao em onboarding | medio | suite de testes API + fluxo frontend minimo |

## Estrategia de Execucao

1. Auditar status e evidencias das SPECs alvo.
2. Normalizar artefatos de governanca.
3. Implementar controle de acesso em endpoints sensiveis.
4. Validar e ajustar fluxo operacional do onboarding.
5. Consolidar evidencias e atualizar status final da SPEC_020.

## Dependencias

- src/api/routes/onboarding.py
- src/api/main.py
- tests/api/test_onboarding.py
- docs/SDD/README.md

## Criterios de Pronto do Plano

- [ ] Plano rastreavel para a SPEC
- [ ] Dependencias mapeadas
- [ ] Riscos com mitigacao
- [ ] Pronto para execucao via tasks.json
