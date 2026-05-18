---
name: handoff
description: Prepara handoff operacional completo para continuidade por humano/agente sem perda de contexto, decisão ou evidência.
reference:
  - https://github.com/mattpocock/skills/tree/main/skills/productivity/handoff
tools:
  - Read
  - Bash
activation_hints:
  - "use handoff"
  - "preparar handoff"
  - "passar contexto"
  - "transição de execução"
  - "handover"
---

# Skill: Handoff

## Mission

Transferir trabalho em andamento com contexto suficiente para continuidade
imediata, evitando retrabalho e decisões perdidas.

## When to use

- Encerramento de sessão com trabalho parcial/completo.
- Troca de responsável (humano ou outro agente).
- Entrega de pacote para execução/revisão posterior.

## Inputs mínimos

- Objetivo da tarefa e estado atual.
- Arquivos alterados e decisões tomadas.
- Evidências de validação (lint, testes, logs, comandos).
- Pendências, riscos e bloqueios conhecidos.

## Execution protocol

1. **State snapshot**

- Registrar objetivo, escopo e status atual.
- Marcar claramente o que está concluído vs pendente.

1. **Decision log**

- Documentar decisões relevantes e racional.
- Incluir alternativas descartadas quando impactarem próximos passos.

1. **Artifact map**

- Listar arquivos/documentos alterados com propósito de cada um.
- Incluir caminhos e referências úteis para retomada.

1. **Validation evidence**

- Consolidar resultados de lint/test/execução.
- Indicar comandos usados e resultados esperados.

1. **Risk and blockers**

- Enumerar riscos residuais e bloqueios ativos.
- Explicitar dependências externas/humanas.

1. **Next-step plan**

- Definir próximo passo objetivo e ordem sugerida.
- Incluir condição de entrada para avançar.

1. **Human gate**

- Submeter handoff para confirmação de entendimento.
- Ajustar nível de detalhe conforme necessidade do receptor.

## Davi governance gates

- Handoff não pode omitir decisão que impacte qualidade/escopo.
- Se houver conflito com regras RN/RA/RG, registrar explicitamente.
- Pendência crítica deve ser destacada como bloqueio real.

## Output obrigatório

- Status: `ready-for-handoff` | `blocked`
- Resumo do estado atual
- Decisões tomadas
- Artefatos alterados
- Evidências de validação
- Riscos/bloqueios
- Próximo passo recomendado

## Quality rules

- Handoff deve ser acionável sem contexto implícito.
- Resumo deve ser curto, mas completo no que importa.
- Evitar texto genérico; priorizar fatos verificáveis.
- Clareza sobre "o que fazer agora" é mandatória.
