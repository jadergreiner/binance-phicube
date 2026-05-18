---
name: grill-me
description: Faz questionamento crítico estruturado sobre plano, decisão ou solução para elevar qualidade antes de executar.
reference:
  - https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me
tools:
  - Read
  - Bash
activation_hints:
  - "use grill-me"
  - "me confronte"
  - "desafiar plano"
  - "stress test da solução"
  - "criticar proposta"
---

# Skill: Grill Me

## Mission

Aplicar pressão intelectual útil sobre uma proposta para expor lacunas,
pressupostos frágeis e riscos ocultos antes da execução.

## When to use

- Plano parece bom, mas risco de cegueira de confirmação é alto.
- Decisão é relevante e reversão seria cara.
- Usuário pede revisão crítica sem complacência.

## Inputs mínimos

- Proposta/plano/decisão a ser testada.
- Objetivo principal e restrições.
- Critérios de sucesso e limite de risco aceitável.
- Contexto de negócio/técnico disponível.

## Execution protocol

1. **Restate proposal clearly**

- Reescrever proposta em termos verificáveis.
- Tornar explícitos objetivos, premissas e dependências.

1. **Assumption stress test**

- Listar pressupostos críticos.
- Para cada pressuposto, perguntar:
  - e se estiver errado?
  - como detectar cedo?
  - qual plano de contingência?

1. **Failure mode analysis**

- Identificar modos de falha por dimensão:
  - produto/negócio
  - técnica/arquitetura
  - operação/suporte
  - governança/compliance

1. **Alternative challenge**

- Gerar 2-3 alternativas viáveis.
- Comparar custo, risco, tempo e reversibilidade.

1. **Decision hardening**

- Recomendar ajustes para reduzir risco com menor custo.
- Definir gatilhos de rollback e sinais de alerta.

1. **Human gate**

- Submeter pontos críticos e recomendações ao humano.
- Confirmar decisão final antes de execução.

1. **Closeout**

- Consolidar decisão endurecida e próximos passos.

## Davi governance gates

- Se houver conflito com RN/RA/RG aprovadas, voltar aos refinadores.
- Não aprovar execução de proposta com risco crítico sem mitigação.
- Quando houver incerteza alta, preferir plano reversível.

## Output obrigatório

- Status: `ready` | `blocked`
- Proposta resumida
- Premissas críticas e fragilidades
- Modos de falha prioritários
- Alternativas comparadas
- Recomendação final endurecida
- Decisão humana pendente/aprovada

## Quality rules

- Crítica deve ser específica, não genérica.
- Confrontar ideias, não pessoas.
- Todo risco relevante deve vir com mitigação proposta.
- Objetivo é melhorar decisão, não bloquear por bloquear.
