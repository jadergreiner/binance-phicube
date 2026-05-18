---
name: write-a-skill
description: Define e escreve novas skills acionáveis pelo Codex com estrutura padrão, gatilhos claros e protocolo operacional verificável.
reference:
  - https://github.com/mattpocock/skills/tree/main/skills/productivity/write-a-skill
tools:
  - Read
  - Bash
activation_hints:
  - "use write-a-skill"
  - "criar skill"
  - "definir skill nova"
  - "skill authoring"
  - "padronizar skill"
---

# Skill: Write A Skill

## Mission

Projetar e documentar uma skill reutilizável, acionável e auditável para o
Codex, mantendo consistência com o core do Davi.

## When to use

- Precisamos criar skill nova para fluxo recorrente.
- Skill atual está vaga e precisa virar protocolo operacional.
- Há necessidade de replicar padrão de skill para outros domínios.

## Inputs mínimos

- Nome da skill e domínio alvo.
- Problema que a skill resolve.
- Contexto de uso e limites de escopo.
- Regras de governança aplicáveis (RN/RA/RG, HITL, SDD).

## Execution protocol

1. **Define purpose and scope**

- Descrever claramente a missão da skill.
- Delimitar quando usar e quando não usar.

1. **Specify operational contract**

- Definir entradas mínimas necessárias.
- Definir saída obrigatória e critérios de qualidade.

1. **Design execution steps**

- Estruturar protocolo em etapas objetivas e verificáveis.
- Evitar linguagem abstrata sem ação concreta.

1. **Add governance gates**

- Incluir decisões que exigem aprovação humana.
- Definir condições de bloqueio e retorno para refinadores.

1. **Add activation metadata**

- Preencher frontmatter acionável:
  - `name`
  - `description`
  - `tools`
  - `activation_hints`
  - `reference` (quando houver)

1. **Validate skill quality**

- Checar clareza, aplicabilidade e ausência de ambiguidades críticas.
- Rodar `markdownlint` e normalizar UTF-8/newline.

1. **Update taxonomy docs**

- Atualizar README do domínio para refletir status real da skill.
- Sincronizar catálogo/roteador quando aplicável.

1. **Human gate**

- Submeter skill criada/atualizada para aprovação humana.
- Ajustar formato/conteúdo conforme feedback.

## Davi governance gates

- Skill não pode contradizer políticas centrais do orquestrador.
- Skill sem protocolo verificável não deve ser marcada como implementada.
- Mudanças de comportamento transversal exigem validação humana.

## Output obrigatório

- Status: `implemented` | `updated` | `blocked`
- Skill criada/atualizada
- Arquivos alterados
- Resultado de lint
- Pendências para aprovação humana
- Próximo passo recomendado

## Quality rules

- Skill deve ser acionável por gatilho textual claro.
- Etapas devem ser concretas e auditáveis.
- Evitar boilerplate sem utilidade operacional.
- Manter padrão de documentação consistente no core.
