---
name: setup-matt-pocock-skills
description: Configura e replica skills do repositório mattpocock/skills para o core do Davi com estrutura, rastreabilidade e validação.
reference:
  - https://github.com/mattpocock/skills/tree/main/skills/engineering/setup-matt-pocock-skills
tools:
  - Read
  - Bash
activation_hints:
  - "use setup-matt-pocock-skills"
  - "instalar skills matt pocock"
  - "replicar estrutura de skills"
  - "bootstrap de skills"
  - "atualizar catálogo de skills"
---

# Skill: Setup Matt Pocock Skills

## Mission

Padronizar a adoção de skills externas no core do Davi, garantindo estrutura
replicável, metadados acionáveis e controle de qualidade documental.

## When to use

- Inicializar catálogo de skills no agente Davi.
- Replicar novas skills de `mattpocock/skills` para o core.
- Sincronizar estrutura de domínios (`engineering`, `misc`, `personal`,
  `productivity`).

## Inputs mínimos

- Fonte de referência (link/commit/tag da skill).
- Domínio e nome da skill destino.
- Regra de adaptação para Davi (gates, HITL, SDD, governança).
- Repositório-alvo (`agent-davi`) e caminho de instalação.

## Execution protocol

1. **Source selection**

- Definir origem exata (URL e, se possível, commit SHA).
- Confirmar skill alvo e domínio de destino.

1. **Structure sync**

- Garantir existência da pasta:
  - `templates/davi-orchestrator/core/skills/<domain>/<skill>/`
- Manter `README.md` do domínio consistente com status real.

1. **Adaptation for Davi**

- Converter conteúdo para `SKILL.md` acionável pelo Codex com:
  - frontmatter (`name`, `description`, `tools`, `activation_hints`)
  - protocolo de execução objetivo
  - gates de governança Davi
  - output obrigatório
- Preservar intenção da skill original sem copiar boilerplate irrelevante.

1. **Quality checks**

- Validar Markdown (`markdownlint`).
- Normalizar UTF-8 sem BOM e newline final único.
- Verificar coerência de termos e caminhos.

1. **Catalog update**

- Atualizar:
  - `core/skills/<domain>/README.md`
  - catálogo/roteador de skills quando aplicável.
- Marcar `implemented` vs `scaffold` de forma explícita.

1. **Human gate**

- Submeter resumo da skill instalada e impactos.
- Não aplicar rollout em consumidores sem autorização humana.

1. **Replication plan (optional)**

- Se autorizado, preparar plano para replicar no(s) repositório(s)
  consumidor(es).

## Davi governance gates

- Não sobrescrever skills existentes sem diff explícito.
- Alteração de comportamento do core exige aprovação humana.
- Regras de projeto consumidor não devem ser misturadas ao core do agente.

## Output obrigatório

- Status: `implemented` | `updated` | `blocked`
- Fonte usada (URL/commit)
- Skill criada/atualizada e domínio
- Arquivos alterados
- Resultado do lint
- Necessidade de replicação em consumidores (`yes/no`)

## Quality rules

- Evitar cópia cega; adaptar ao modelo Davi.
- Garantir reprodutibilidade da instalação da skill.
- Toda skill deve ser acionável por gatilho textual claro.
- Manter documentação de domínio sempre sincronizada.
