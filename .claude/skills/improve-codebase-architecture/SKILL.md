---
name: improve-codebase-architecture
description: Avalia e evolui arquitetura do codebase com foco em boundaries, acoplamento, coesão, testabilidade e plano incremental de refatoração segura.
reference:
  - https://github.com/mattpocock/skills/tree/main/skills/engineering/improve-codebase-architecture
tools:
  - Read
  - Bash
activation_hints:
  - "use improve-codebase-architecture"
  - "melhorar arquitetura"
  - "refatoração estrutural"
  - "reduzir acoplamento"
  - "modularizar"
---

# Skill: Improve Codebase Architecture

## Mission

Produzir melhoria arquitetural objetiva e incremental sem quebrar comportamento,
com rastreabilidade de decisões, trade-offs e impacto operacional.

## When to use

- Código difícil de manter, com alto acoplamento e baixa coesão.
- Mudanças frequentes gerando regressões em áreas transversais.
- Necessidade de modularizar, separar responsabilidades ou redefinir boundaries.

## Inputs mínimos

- Objetivo de evolução (ex.: modularização, isolamento de domínio, contrato).
- Área/sistema alvo e restrições de negócio.
- Regras aprovadas (RN/RA/RG) e artefatos ativos (PRD/SPEC/Tasks quando houver).
- Estado atual de testes e cobertura mínima para proteção de refatoração.

## Execution protocol

1. **Baseline arquitetural**

- Mapear módulos, dependências e fluxos críticos.
- Identificar pontos de dor com evidência:
  - ciclos de dependência
  - responsabilidades misturadas
  - baixa testabilidade
  - vazamento de abstração

1. **Define target architecture**

- Definir estado-alvo com boundaries explícitos:
  - domínio
  - aplicação
  - infraestrutura
  - interfaces/contratos
- Estabelecer invariantes que não podem ser quebradas.

1. **Gap analysis**

- Comparar estado atual vs estado-alvo.
- Classificar gaps por severidade e custo:
  - `critical`
  - `high`
  - `medium`
  - `low`

1. **Incremental migration plan**

- Quebrar em lotes pequenos e reversíveis.
- Para cada lote, definir:
  - objetivo
  - arquivos/componentes afetados
  - risco
  - critério de aceite
  - rollback
- Priorizar mudanças que reduzem risco sistêmico primeiro.

1. **Validation strategy**

- Definir bateria de validação por lote:
  - testes de contrato
  - testes de integração
  - smoke operacional
- Reforçar observabilidade antes de mudanças críticas.

1. **Human architecture gate**

- Submeter trade-offs e plano incremental ao humano.
- Bloquear execução se houver conflito com regras aprovadas.
- Se escopo mudar, voltar ao fluxo de refinamento SDD.

1. **Execution guardrails**

- Aplicar refatorações por lote aprovado.
- Evitar big bang rewrite.
- Validar cada lote antes de avançar ao próximo.

1. **Closeout**

- Registrar decisões arquiteturais finais (ADR/CONTEXT).
- Consolidar ganhos, riscos residuais e próximos passos.

## Davi governance gates

- Mudança arquitetural de alto impacto exige aprovação humana formal.
- Divergência com RN/RA/RG deve escalar para refinadores.
- Sem critério de rollback explícito, lote não pode iniciar.

## Output obrigatório

- Status: `ready` | `blocked` | `in-progress`
- Baseline arquitetural resumido
- Estado-alvo e princípios adotados
- Gaps priorizados com impacto
- Plano incremental por lotes + rollback
- Estratégia de validação
- Decisões humanas registradas
- Riscos residuais e próximo passo

## Quality rules

- Não executar reescrita total sem justificativa formal.
- Não misturar refatoração estrutural com mudança funcional não aprovada.
- Toda alteração arquitetural deve preservar rastreabilidade de decisão.
- Progresso deve ser incremental, testável e reversível.
