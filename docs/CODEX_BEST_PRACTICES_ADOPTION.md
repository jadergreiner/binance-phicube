# Adocao de Best Practices do Codex (OpenAI)

Data: 2026-05-08  
Fontes:
- https://developers.openai.com/codex/learn/best-practices
- https://developers.openai.com/codex/skills?utm_source=chatgpt.com

## Objetivo

Incorporar no Phicube as praticas recomendadas para melhorar previsibilidade, qualidade de review e velocidade operacional com agentes.

## Mudancas incorporadas no repositorio

1. `AGENTS.md` raiz com regras duraveis de execucao.
2. `PLANS.md` para tarefas complexas e multi-etapas.
3. `code_review.md` com checklist de revisao tecnica.
4. `.codex/config.toml` repo-specific com politica conservadora de aprovacao/sandbox.
5. `docs/CODEX_TASK_TEMPLATE.md` para padronizar prompts com Goal/Context/Constraints/Done when.
6. `tools/phicube_ops_cli.py doctor` e `scripts/skills/validate_skills_adoption.py` atualizados para validar a presenca desses artefatos.

## Mapeamento das recomendacoes oficiais para o Phicube

- Contexto e prompts fortes: `docs/CODEX_TASK_TEMPLATE.md` padroniza `Goal/Context/Constraints/Done when`.
- Planejar tarefas dificeis: `PLANS.md` e regra operacional em `AGENTS.md`.
- Guia reutilizavel por repo: `AGENTS.md` com comandos, regras, definicao de pronto e anti-padroes.
- Configuracao consistente: `.codex/config.toml` com sandbox e aprovacoes conservadoras.
- Confiabilidade por teste/review: `code_review.md` + exigencia de lint/teste/validacao.
- MCP e skills com foco em ROI: adocao priorizada em `docs/SKILLS_ADOPTION_PLAYBOOK.md`.
- Skills com descricao de gatilho e escopo unico: aplicadas em `.codex/skills/*/SKILL.md` e validadas por script.
- Automacoes apenas apos estabilidade manual: backlog explicitado neste documento.
- Higiene de sessao: regra de uma thread por tarefa e uso de fork/worktree em `AGENTS.md`.

## Decisoes criticas

- Menor privilegio por padrao (`approval_policy=on-request`, `sandbox_mode=workspace-write`).
- Regras estaveis foram movidas para arquivo duravel (`AGENTS.md`) para evitar prompts longos.
- Reuso por checklist/template para reduzir variacao de qualidade entre sessoes.
- Regra de criticidade ativa: quando houver pedido mal especificado, o agente deve sinalizar falha de qualidade e solicitar ajuste minimo antes de continuar.

## Backlog de evolucao (quando houver maturidade)

- Automacao agendada no app do Codex para:
  - resumo semanal de commits,
  - triagem de falhas de CI,
  - resumo de friccoes recorrentes para atualizar `AGENTS.md`.
- Expandir skills apenas em loops realmente repetitivos, evitando inflar stack cedo.

## Erros comuns que o time deve evitar

- Iniciar mudanca grande sem plano.
- Pedir implementacao sem criterio objetivo de pronto.
- Exigir permissao ampla por conveniencia e nao por necessidade.
- Tratar tarefa recorrente como prompt ad-hoc em vez de skill.
- Automatizar fluxo instavel antes de estabilizar execucao manual.

## Como validar localmente

```bash
python tools/phicube_ops_cli.py doctor --json
python scripts/skills/validate_skills_adoption.py
```
