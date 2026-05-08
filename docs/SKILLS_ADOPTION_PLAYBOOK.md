# Skills Adoption Playbook (Phicube)

Data: 2026-05-08
Referencia: https://composio.dev/content/top-codex-skills
Referencia complementar: https://developers.openai.com/codex/skills?utm_source=chatgpt.com

## Objetivo

Implementar adocao enxuta de skills para aumentar:

- velocidade de diagnostico de CI
- rigor de modelagem de ameacas
- padronizacao de comandos operacionais

Sem adicionar passos obrigatorios para fluxos simples.

## Recomendacoes oficiais de Skills (OpenAI) aplicadas

- Skill deve ter escopo unico e claro (um trabalho por skill).
- Descricao deve ser curta, objetiva e com gatilho explicito de uso (`Use when ...`).
- Priorizar instrucoes em `SKILL.md`; usar `scripts/` apenas quando exigir comportamento deterministico ou integracao externa.
- Workflow deve declarar entradas/saidas e passos imperativos verificaveis.
- Usar invocacao explicita (`$skill`) para tarefas sensiveis; manter invocacao implicita quando o trigger estiver bem definido.
- Tratar skills como formato de autoria; usar plugin quando houver necessidade de distribuicao reutilizavel fora do repo.
- Evitar inflar stack local de skills para nao degradar descoberta implicita por limite de contexto.

Complemento de governanca do Codex:

- `AGENTS.md` (regras duraveis)
- `code_review.md` (checklist de review)
- `docs/CODEX_TASK_TEMPLATE.md` (template de prompt)
- `docs/CODEX_BEST_PRACTICES_ADOPTION.md` (adocao oficial OpenAI)

## Skills Priorizadas

1. `gh-fix-ci` (instalado em `.codex/skills/gh-fix-ci`)
2. `security-threat-model` (skill local em `.codex/skills/security-threat-model`)
3. `cli-creator` (skill local em `.codex/skills/cli-creator`)

Ja cobertos anteriormente:

- `create-plan`
- `webapp-testing`

Backlog condicionado (nao implementado agora):

- `connect`
- `notion-spec-to-implementation`
- `mcp-builder`

## Como Usar

### 1) CI triage com gh-fix-ci

```bash
python .codex/skills/gh-fix-ci/scripts/inspect_pr_checks.py --repo . --pr <numero-ou-url-pr>
```

### 2) Threat model repo-grounded

```bash
python .codex/skills/security-threat-model/scripts/generate_threat_model.py --repo . --overwrite
```

Saida padrao:

`reports/threat-models/binance-phicube-threat-model.md`

### 3) CLI operacional reutilizavel

```bash
python tools/phicube_ops_cli.py --help
python tools/phicube_ops_cli.py doctor --json
python tools/phicube_ops_cli.py ci-inspect --pr <numero-ou-url-pr>
```

## Validacao dos 3 Cenarios do Plano

Executar:

```bash
python scripts/skills/validate_skills_adoption.py
```

Esse comando valida:

1. smoke test do `gh-fix-ci`
2. geracao de threat model
3. health check da CLI operacional
4. aderencia minima dos artefatos Codex
5. aderencia minima das skills priorizadas as recomendacoes oficiais
