---
name: zoom-out
description: Amplia a visão sistêmica da proposta para avaliar impacto transversal, riscos de segunda ordem e alinhamento estratégico antes de executar.
reference:
  - https://github.com/mattpocock/skills/tree/main/skills/engineering/zoom-out
tools:
  - Read
  - Bash
activation_hints:
  - "use zoom-out"
  - "visão sistêmica"
  - "avaliar impacto macro"
  - "análise de segunda ordem"
  - "perspectiva estratégica"
---

# Skill: Zoom Out

## Mission

Elevar a análise do nível local para o nível sistêmico, evitando decisões
otimizadas localmente que degradam arquitetura, operação ou estratégia.

## When to use

- Decisão técnica com impacto em múltiplos módulos/equipes.
- Situação com trade-offs relevantes entre curto e longo prazo.
- Mudança que pode afetar roadmap, governança ou operação contínua.

## Inputs mínimos

- Proposta/decisão atual e objetivo imediato.
- Contexto arquitetural e de produto ativo.
- Restrições de negócio, operação e governança.
- Horizonte de análise (curto, médio, longo prazo).

## Execution protocol

1. **Reframe objective**

- Reescrever o objetivo em termos de resultado sistêmico.
- Separar objetivo local de impacto global esperado.

1. **System surface mapping**

- Mapear superfícies afetadas:
  - domínio de negócio
  - arquitetura e dependências
  - operação/observabilidade
  - segurança/compliance
  - experiência do usuário

1. **Second-order effects**

- Identificar efeitos indiretos e acoplamentos ocultos.
- Avaliar consequências de manutenção, escalabilidade e custo operacional.

1. **Option set and trade-offs**

- Comparar 2-4 opções viáveis.
- Para cada opção, explicitar:
  - benefícios
  - custos
  - riscos
  - reversibilidade

1. **Strategic alignment check**

- Validar aderência com regras RN/RA/RG e direção do projeto.
- Marcar divergências e lacunas de decisão.

1. **Decision gate with human**

- Submeter recomendação e trade-offs ao humano.
- Não avançar em opção de alto impacto sem aprovação formal.

1. **Action framing**

- Traduzir decisão aprovada em próximos passos executáveis.
- Indicar se segue para refinadores, RCA ou implementação.

## Davi governance gates

- Divergência estratégica deve retornar ao fluxo de refinamento.
- Decisão irreversível exige aprovação humana explícita.
- Sem clareza de impacto sistêmico, status deve permanecer `blocked`.

## Output obrigatório

- Status: `ready` | `blocked`
- Objetivo reframeado
- Mapa de superfícies impactadas
- Efeitos de segunda ordem identificados
- Opções comparadas e trade-offs
- Recomendação com justificativa
- Decisão humana pendente/aprovada
- Próximo passo operacional

## Quality rules

- Evitar recomendações baseadas apenas no ganho local.
- Trade-offs devem ser explícitos e verificáveis.
- Priorizar decisões reversíveis quando incerteza é alta.
- Registrar claramente o racional da decisão final.
