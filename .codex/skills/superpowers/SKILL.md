---
name: superpowers
description: Protocolo SuperPowers para conduzir desenvolvimento guiado por especificacao com fluxo obrigatorio brainstorm -> plano -> testes -> implementacao -> review. Use quando precisar transformar uma demanda em execucao rastreavel ponta a ponta. Nao use para tarefas triviais de uma unica edicao sem necessidade de artefatos.
argument-hint: objetivo + contexto (ex: corrigir reconciliacao de posicoes no monitor)
---

# SuperPowers Skill Protocol - Phicube

Skill operacional para organizar trabalho tecnico com rastreabilidade, criterios de aceite claros e memoria de decisao.

## Acionamento

- Comando recomendado: `/superpowers <objetivo + contexto>`
- Exemplo: `/superpowers corrigir falso CLOSED_MANUAL no monitor de ordens`

## Protocolo Obrigatorio

Executar sempre nesta ordem:

1. Brainstorm
2. Plano
3. Testes
4. Implementacao
5. Review

Nao sinalizar conclusao enquanto existir etapa pendente.

## Artefatos Obrigatorios

Para execucao vinculada a SPEC (`docs/SDD/SPEC_NNN_.../`), criar/atualizar:

- `superpowers_brainstorm.md`
- `plan.md`
- `superpowers_test_plan.md`
- `superpowers_implementation_log.md`
- `superpowers_review.md`
- `tasks_status.json`
- `spec_status_update.md`

Para execucao sem SPEC formal, criar artefatos equivalentes em pasta de trabalho definida no inicio da tarefa.

## Memoria Operacional Obrigatoria

Ler no inicio e atualizar ao final:

- `.ai/memory/project.md`
- `.ai/memory/decisions.md`
- `.ai/memory/corrections.md`
- `.ai/memory/prompts.md`

Regras:
- Registrar apenas fatos verificaveis
- Entradas curtas e datadas
- Nao duplicar historico sem necessidade

## Templates

Usar os templates desta skill como base:

- `templates/superpowers_brainstorm.template.md`
- `templates/superpowers_plan.template.md`
- `templates/superpowers_test_plan.template.md`
- `templates/superpowers_implementation_log.template.md`
- `templates/superpowers_review.template.md`

## Checklist de Saida

- Fluxo completo executado
- Evidencias de teste registradas
- Riscos residuais declarados
- Estado final claro (aprovado, pendente, bloqueado)

