---
name: triage
description: Faz triagem estruturada de demandas/incidentes para priorizar execução por impacto, urgência, risco e esforço.
reference:
  - https://github.com/mattpocock/skills/tree/main/skills/engineering/triage
tools:
  - Read
  - Bash
activation_hints:
  - "use triage"
  - "priorizar backlog"
  - "fazer triagem"
  - "classificar incidente"
  - "ordenar tarefas"
---

# Skill: Triage

## Mission

Classificar e priorizar itens de trabalho com critérios objetivos, reduzindo
fila caótica e criando sequência clara para execução.

## When to use

- Há múltiplas demandas concorrentes sem prioridade definida.
- Entrada de bugs/incidentes precisa de classificação rápida.
- Time precisa decidir o próximo lote de execução.

## Inputs mínimos

- Lista de itens (bug, melhoria, débito, incidente, request).
- Contexto mínimo de cada item (sintoma/objetivo).
- Restrições ativas (SLA, janela operacional, dependências).
- Critérios de negócio/governança aplicáveis (RN/RA/RG).

## Execution protocol

1. **Normalize backlog items**

- Padronizar cada item com campos mínimos:
  - título
  - tipo
  - contexto
  - impacto esperado
  - evidência disponível

1. **Classify severity and urgency**

- Atribuir severidade (`critical`, `high`, `medium`, `low`).
- Atribuir urgência (imediato, curto prazo, planejado).

1. **Assess impact and risk**

- Avaliar impacto em:
  - negócio
  - cliente/operação
  - arquitetura/qualidade
  - compliance/governança
- Avaliar risco de não fazer.

1. **Estimate effort and dependencies**

- Estimar esforço relativo (S, M, L, XL).
- Mapear bloqueios e dependências entre itens.

1. **Prioritize queue**

- Ordenar itens por valor-risco-urgência-esforço.
- Separar quick wins de itens estruturais.

1. **Route by flow type**

- Direcionar cada item para fluxo adequado:
  - `Q&A`
  - `RCA`
  - `New Implementation`
- Indicar quando item precisa voltar para refinadores.

1. **Human triage gate**

- Submeter ranking e decisões de prioridade ao humano.
- Bloquear execução de itens controversos sem aprovação.

1. **Closeout**

- Publicar fila priorizada com justificativas e próximo lote recomendado.

## Davi governance gates

- Itens que conflitam com regras aprovadas devem retornar ao gate de refinamento.
- Incidentes críticos podem elevar prioridade, mas exigem registro de decisão.
- Sem evidência mínima, item não deve ser promovido para execução.

## Output obrigatório

- Status: `ready` | `blocked`
- Backlog normalizado
- Ranking priorizado com justificativas
- Dependências e bloqueios
- Roteamento por fluxo (`Q&A`, `RCA`, `New Implementation`)
- Aprovações humanas pendentes
- Próximo lote recomendado

## Quality rules

- Priorização deve ser explicável e auditável.
- Evitar priorizar por percepção subjetiva sem critério.
- Manter separação clara entre urgência e importância.
- Reavaliar ranking quando contexto de negócio mudar.
