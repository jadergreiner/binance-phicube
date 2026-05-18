---
name: git-guardrails-claude-code
description: Aplica guardrails de Git para evitar operações destrutivas e garantir commits seguros, rastreáveis e mínimos durante execução por agentes.
reference:
  - https://github.com/mattpocock/skills/tree/main/skills/misc/git-guardrails-claude-code
tools:
  - Read
  - Bash
activation_hints:
  - "use git-guardrails"
  - "proteger fluxo git"
  - "commit seguro"
  - "evitar reset hard"
  - "git hygiene"
---

# Skill: Git Guardrails (Claude Code)

## Mission

Executar operações Git com segurança operacional, minimizando risco de perda de
trabalho e evitando alterações fora de escopo.

## When to use

- Antes de `add/commit/push` em mudanças relevantes.
- Ao resolver conflitos, rebase ou merge manual.
- Em repositórios com worktree suja ou alterações paralelas de outros agentes.

## Inputs mínimos

- Escopo aprovado da mudança.
- Repositório e branch alvo.
- Lista de arquivos esperados para commit.
- Regras do time para convenção de commit e publicação.

## Execution protocol

1. **Preflight status**

- Verificar estado atual (`git status --short`, branch ativa).
- Detectar alterações fora do escopo solicitado.

1. **Scope lock**

- Definir explicitamente quais arquivos entram no commit.
- Excluir arquivos incidentais ou temporários não aprovados.

1. **Safety checks**

- Proibir comandos destrutivos sem autorização explícita:
  - `git reset --hard`
  - `git checkout -- <file>`
  - reescrita de histórico em branch compartilhada
- Se necessário, solicitar gate humano antes da ação.

1. **Conflict handling**

- Em conflito de merge/rebase:
  - preservar mudanças válidas locais
  - resolver por menor dif correto
  - revalidar arquivos resolvidos
- Não remover alterações do usuário sem autorização.

1. **Commit discipline**

- Commit pequeno, coeso e rastreável.
- Mensagem no padrão do projeto (ex.: `feat:`, `fix:`, `docs:`, `chore:`).
- Incluir apenas arquivos do escopo travado.

1. **Push discipline**

- Confirmar branch/remoto corretos antes do push.
- Evitar `--force` sem aprovação humana formal.

1. **Post-push verification**

- Registrar hash e range publicado.
- Confirmar estado local limpo para o escopo tratado.

## Davi governance gates

- Toda ação destrutiva exige aprovação humana explícita.
- Conflito entre mudanças de usuário e agente deve pausar para decisão humana.
- Se houver risco de escopo excedido, bloquear e revalidar com refinadores.

## Output obrigatório

- Status: `ready` | `blocked` | `completed`
- Branch/remoto alvo
- Arquivos incluídos no commit
- Comandos Git executados
- Hash(es) gerados/publicados
- Riscos/pendências identificados

## Quality rules

- Nunca usar atalho destrutivo por conveniência.
- Commits devem ser mínimos e semanticamente consistentes.
- Push deve preservar histórico seguro por padrão.
- Toda exceção de guardrail deve ser documentada.
