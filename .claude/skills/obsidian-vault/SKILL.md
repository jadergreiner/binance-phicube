---
name: obsidian-vault
description: Estrutura e mantém um Obsidian Vault com notas conectadas, padrões de captura e organização para conhecimento reutilizável.
reference:
  - https://github.com/mattpocock/skills/tree/main/skills/personal/obsidian-vault
tools:
  - Read
  - Bash
activation_hints:
  - "use obsidian-vault"
  - "organizar vault"
  - "estruturar notas"
  - "mapa de conhecimento"
  - "obsidian"
---

# Skill: Obsidian Vault

## Mission

Organizar conhecimento no Obsidian de forma navegável e sustentável, com
estrutura consistente, links úteis e baixo atrito de manutenção.

## When to use

- Vault está desorganizado ou difícil de navegar.
- Necessidade de padronizar captura e revisão de conhecimento.
- Desejo de criar sistema de notas reutilizável para estudo/projetos.

## Inputs mínimos

- Estado atual do vault (pastas, notas, convenções existentes).
- Objetivo de uso (estudo, projeto, pesquisa, diário técnico).
- Nível de granularidade desejado para notas.
- Regras de nomenclatura e idioma preferidos.

## Execution protocol

1. **Vault audit**

- Mapear estrutura atual e pontos de atrito.
- Identificar redundâncias, notas órfãs e padrões conflitantes.

1. **Information architecture**

- Definir organização base (pastas, tags, índices/MOCs).
- Estabelecer convenções de nome e metadados mínimos.

1. **Template definition**

- Criar templates para tipos de nota mais frequentes:
  - referência
  - projeto
  - ideia
  - tarefa
  - resumo

1. **Linking strategy**

- Definir padrão de links internos e backlinks úteis.
- Criar notas-hub para temas centrais.

1. **Capture and review workflow**

- Definir fluxo simples de captura (inbox -> processamento -> arquivo).
- Definir rotina de revisão periódica e limpeza.

1. **Migration pass**

- Aplicar reorganização incremental em lotes.
- Evitar mudanças destrutivas sem backup.

1. **Human gate**

- Submeter estrutura e convenções ao humano.
- Ajustar conforme preferência real de uso.

1. **Closeout**

- Entregar vault estruturado com guia rápido de operação.

## Davi governance gates

- Não apagar conteúdo sem confirmação explícita.
- Em reorganização ampla, recomendar backup prévio obrigatório.
- Mudanças de convenção devem ser documentadas para consistência futura.

## Output obrigatório

- Status: `ready` | `blocked` | `completed`
- Diagnóstico do vault
- Estrutura proposta/aplicada
- Templates definidos
- Estratégia de links e revisão
- Decisões humanas registradas
- Próximo passo operacional

## Quality rules

- Estrutura deve reduzir atrito, não aumentar burocracia.
- Organização precisa ser estável e fácil de manter.
- Links devem priorizar utilidade real de navegação.
- Evolução do vault deve ser incremental e reversível.
