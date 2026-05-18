---
name: to-issues
description: Converte escopo aprovado (PRD/SPEC/Tasks) em issues executáveis, pequenas e rastreáveis para implementação.
reference:
  - https://github.com/mattpocock/skills/tree/main/skills/engineering/to-issues
tools:
  - Read
  - Bash
activation_hints:
  - "use to-issues"
  - "quebrar em issues"
  - "gerar issues de execução"
  - "transformar tasks em tickets"
  - "issue breakdown"
---

# Skill: To Issues

## Mission

Transformar artefatos de especificação aprovados em issues claras, independentes
e priorizadas, prontas para execução por times/agentes executores.

## When to use

- Após aprovação de PRD/SPEC/Plan/Tasks.
- Quando há escopo amplo e precisa de decomposição operacional.
- Para organizar backlog de execução com dependências explícitas.

## Inputs mínimos

- Artefato-fonte aprovado (SPEC/Tasks/Plan).
- Critérios de aceite e restrições já definidos.
- Dependências e ordem de execução esperada.
- Convenções de issue do projeto (labels, prioridade, owner, definição de done).

## Execution protocol

1. **Ingest approved scope**

- Ler apenas artefatos aprovados para a decomposição.
- Rejeitar fonte em draft sem aprovação formal.

1. **Extract work units**

- Identificar unidades de trabalho atômicas por resultado verificável.
- Evitar issues grandes que misturam múltiplos objetivos.

1. **Define issue contract**

- Para cada issue, preencher:
  - título objetivo
  - contexto
  - escopo dentro/fora
  - checklist de implementação
  - critérios de aceite binários
  - evidência esperada

1. **Set dependencies and sequencing**

- Declarar bloqueios e paralelismo possível.
- Ordenar por risco/impacto e caminho crítico.

1. **Assign governance metadata**

- Definir prioridade, tipo, owner sugerido e labels.
- Ligar cada issue ao artefato de origem (rastreabilidade).

1. **Human gate**

- Submeter decomposição para aprovação humana.
- Não iniciar execução sem aprovação formal do pacote de issues.

1. **Closeout**

- Entregar backlog final com visão de sequência e dependências.
- Apontar primeiro lote recomendado para execução.

## Davi governance gates

- Não gerar issue fora de escopo aprovado.
- Divergência de regra RN/RA/RG deve voltar aos refinadores.
- Issue sem aceite verificável não pode ser publicada como pronta.

## Output obrigatório

- Status: `ready` | `blocked`
- Quantidade de issues geradas
- Lista de issues com prioridade e dependências
- Mapeamento issue -> artefato de origem
- Pendências para aprovação humana
- Próximo lote recomendado

## Quality rules

- Cada issue deve produzir um resultado observável.
- Dependências devem ser explícitas e mínimas.
- Linguagem de issue deve ser operacional, não genérica.
- Backlog final deve ser executável sem interpretação ambígua.
