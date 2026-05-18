---
name: to-prd
description: Converte demanda bruta ou proposta inicial em PRD estruturado, testável e aprovado por humano antes de implementação.
reference:
  - https://github.com/mattpocock/skills/tree/main/skills/engineering/to-prd
tools:
  - Read
  - Bash
activation_hints:
  - "use to-prd"
  - "gerar PRD"
  - "transformar ideia em PRD"
  - "especificar requisitos de produto"
  - "draft prd"
---

# Skill: To PRD

## Mission

Transformar solicitações de alto nível em PRD claro, mensurável e aprovável,
reduzindo ambiguidade antes da fase de SPEC/Plan/Tasks.

## When to use

- Existe ideia/problema, mas requisitos ainda estão difusos.
- Necessidade de alinhar escopo de produto antes de design técnico.
- Entrada para fluxo SDD em etapa de requisitos.

## Inputs mínimos

- Problema/oportunidade de negócio.
- Público alvo e contexto de uso.
- Restrições conhecidas (prazo, risco, compliance, operação).
- Critérios iniciais de sucesso (mesmo que incompletos).

## Execution protocol

1. **Problem framing**

- Definir problema principal e impacto atual.
- Registrar por que resolver agora.

1. **Outcome definition**

- Definir resultado esperado do ponto de vista do produto.
- Separar resultado de solução técnica.

1. **Scope boundaries**

- Delimitar claramente:
  - dentro do escopo
  - fora do escopo
- Evitar incluir implementação detalhada nesta fase.

1. **Requirements drafting**

- Estruturar requisitos funcionais e não funcionais.
- Garantir cada requisito com critério verificável.

1. **Success metrics**

- Definir métricas objetivas de sucesso.
- Incluir condições de falha/rollback quando aplicável.

1. **Risk and dependency mapping**

- Mapear riscos de produto/negócio/execução.
- Mapear dependências externas e internas.

1. **Human PRD gate**

- Submeter PRD para revisão e aprovação formal.
- Não avançar para SPEC sem aprovação explícita.

1. **Handoff**

- Entregar PRD final com links para próximos artefatos SDD.
- Sugerir próximo passo: SPEC.

## Davi governance gates

- PRD não pode contradizer RN/RA/RG aprovadas sem decisão humana.
- Mudanças de escopo pós-aprovação exigem nova rodada de validação.
- Sem métricas e critérios de aceite, PRD deve permanecer `draft`.

## Output obrigatório

- Status: `draft` | `in-review` | `approved`
- Problema e objetivo de produto
- Escopo dentro/fora
- Requisitos funcionais e não funcionais
- Métricas de sucesso
- Riscos e dependências
- Decisão humana e próximo passo recomendado

## Quality rules

- PRD deve ser orientado a resultado, não a implementação.
- Requisitos devem ser claros, testáveis e sem ambiguidade crítica.
- Não pular gate humano entre PRD e SPEC.
- Linguagem deve ser útil para negócio e execução técnica.
