---
name: prototype
description: Constrói protótipos rápidos e descartáveis para reduzir incerteza técnica antes da implementação final.
reference:
  - https://github.com/mattpocock/skills/tree/main/skills/engineering/prototype
tools:
  - Read
  - Bash
activation_hints:
  - "use prototype"
  - "fazer prova de conceito"
  - "rodar POC"
  - "validar hipótese técnica"
  - "spike técnico"
---

# Skill: Prototype

## Mission

Reduzir risco de implementação com protótipos de baixo custo, foco em hipótese
mensurável e decisão clara de seguir, ajustar ou descartar.

## When to use

- Há incerteza técnica relevante sobre viabilidade.
- Existem múltiplas opções de abordagem sem decisão objetiva.
- A mudança é de alto impacto e exige aprendizado rápido antes do build final.

## Inputs mínimos

- Hipótese técnica a validar.
- Critérios objetivos de sucesso/falha.
- Restrições (tempo, performance, segurança, compatibilidade).
- Escopo máximo do protótipo (tempo e profundidade).

## Execution protocol

1. **Define hypothesis and decision rule**

- Escrever hipótese em formato testável.
- Definir decisão binária com base no resultado:
  - `go`
  - `adjust`
  - `stop`

1. **Constrain scope**

- Delimitar claramente o que o protótipo cobre e o que não cobre.
- Fixar limite de esforço (timebox) e artefatos esperados.

1. **Design minimal experiment**

- Planejar experimento mínimo para validar a hipótese.
- Preferir o menor caminho que produza evidência confiável.

1. **Implement prototype**

- Construir código de experimento isolado, simples e reversível.
- Evitar acoplamento profundo com código de produção.

1. **Measure and record evidence**

- Coletar métricas e resultados observáveis.
- Registrar comandos, inputs, outputs e limitações.

1. **Decision gate with human**

- Apresentar evidências e recomendação (`go/adjust/stop`).
- Bloquear avanço para implementação final sem decisão humana.

1. **Closeout**

- Documentar aprendizado técnico e riscos remanescentes.
- Definir próximos passos: promoção para SPEC/Tasks ou descarte.

## Davi governance gates

- Protótipo não substitui SPEC aprovada para entrega final.
- Se descoberta alterar escopo/regras, retornar ao fluxo de refinadores.
- Não promover código experimental para produção sem hardening explícito.

## Output obrigatório

- Status: `validated` | `partially-validated` | `invalidated`
- Hipótese e regra de decisão
- Escopo do protótipo e limites
- Evidências coletadas (métricas/comandos/resultados)
- Recomendação: `go` | `adjust` | `stop`
- Riscos residuais e próximo passo

## Quality rules

- Protótipo deve ser rápido, explícito e descartável por padrão.
- Evitar poluir código de produção com experimento temporário.
- Sem conclusão sem evidência mensurável.
- Toda promoção de resultado exige aprovação humana.
