# Plan — SPEC_022

## Meta

- spec_id: SPEC_022
- objetivo: Convergir PRD, SDD e codigo para regras criticas de risco e limites operacionais, eliminando divergencias normativas.
- escopo: validacao de leverage maximo, politica de alocacao de capital e alinhamento de escalabilidade/limites.
- fora_de_escopo: multiplas estrategias, auto-otimizacao de parametros, redesign arquitetural distribuido.

## Entradas

- docs/SDD/SPEC_022_CONVERGENCIA_PRD_SDD_CODIGO/SPEC.md
- PRD.md
- docs/SDD/SPEC.md
- docs/SDD/SPEC_021_VALIDACAO_OPERACIONAL_RESILIENCIA/SPEC.md

## Premissas

- A entrega pode exigir mudanca de comportamento no `RiskManager` para aderencia ao PRD.
- O limite de leverage deve ser aplicado na validacao de configuracao, antes de iniciar runtime.
- A convergencia documental e parte obrigatoria do pacote, nao apenas efeito colateral.

## Riscos e Mitigacoes

| risco | impacto | mitigacao |
|---|---|---|
| Regressao em cenarios de sizing existentes | alto | ampliar cobertura de testes de risco e cenarios limite |
| Divergencia remanescente entre docs apos patch de codigo | alto | checklist de rastreabilidade e revisao cruzada PRD/SDD |
| Ambiguidade entre meta futura e limite atual de operacao | medio | explicitar contrato vigente e backlog futuro em secoes distintas |

## Estrategia de Execucao

1. Fechar contrato canonico para leverage e alocacao com base no PRD.
2. Atualizar implementacao e testes dos modulos de configuracao e risco.
3. Harmonizar documentacao PRD/SDD/README com o comportamento final aprovado.
4. Consolidar evidencias de conformidade e atualizar status da SPEC.

## Dependencias

- docs/SDD/SPEC_022_CONVERGENCIA_PRD_SDD_CODIGO/tasks.json
- docs/SDD/SPEC_022_CONVERGENCIA_PRD_SDD_CODIGO/tasks_status.json
- docs/SDD/SPEC_022_CONVERGENCIA_PRD_SDD_CODIGO/spec_status_update.md
- Apropriacao do contrato pelo Time A e Risk Manager

## Criterios de Pronto do Plano

- [ ] Plano rastreavel para a SPEC_022
- [ ] Dependencias mapeadas
- [ ] Riscos com mitigacao
- [ ] Pronto para execucao com task graph

