# AGENTS.md

Guia operacional para agentes neste repositorio.

## Escopo e objetivo

- Projeto: bot de auto trade Binance Futures USDT-M.
- Objetivo de cada tarefa: entregar mudanca pequena, verificavel e segura.
- Idioma padrao de documentacao e mensagens: pt-BR.

## Estrutura relevante do repo

- `src/`: codigo de aplicacao.
- `tests/`: testes unitarios e de integracao.
- `docs/SDD/`: SPECs e fluxo oficial Serena.
- `.codex/skills/`: skills locais do projeto.
- `tools/phicube_ops_cli.py`: CLI operacional reutilizavel.

## Comandos principais

- Instalar dev deps: `pip install -e ".[dev]"`.
- Rodar testes: `pytest`.
- Lint: `ruff check .`.
- Format: `ruff format .`.
- Doctor de operacao: `python tools/phicube_ops_cli.py doctor --json`.
- Validacao de skills/adocao: `python scripts/skills/validate_skills_adoption.py`.

## Regras de execucao

- Em mudancas complexas, planejar antes de codar (modo plano ou `PLANS.md`).
- Em mudancas simples e locais, implementar direto e validar rapidamente.
- Sempre explicitar criterio de pronto (done when) antes de concluir.
- Nunca assumir acesso irrestrito: manter sandbox/aprovacoes no menor privilegio necessario.
- Nao expor segredos em logs, docs, commits ou testes.
- Governanca de mudancas: usar `openspec` oficial como fluxo canonico (`propose`, `explore`, `apply`, `archive`).
- Fluxo compat local (`tools/openspec_local.py`) descontinuado para uso diario a partir de 2026-05-15.

## Higiene de sessao

- Uma thread por tarefa coerente; evitar thread unica para o projeto inteiro.
- Se a tarefa divergir de escopo, usar fork da thread e preservar historico.
- Evitar execucao paralela em cima dos mesmos arquivos sem worktree dedicado.
- Ao repetir um fluxo manual com baixa variacao, empacotar em skill antes de automatizar.

## Puxao de orelha operacional

- Pedido sem `Goal/Context/Constraints/Done when`: pausar e pedir esse minimo.
- Mudanca multi-modulo sem plano: exigir `/plan` ou `PLANS.md` antes de codar.
- Regra recorrente repetida em prompt: mover para `AGENTS.md` ou skill.
- Pedido de permissao ampla sem necessidade: manter menor privilegio e justificar excecao.

## Regras de skills

- Cada skill deve resolver um trabalho especifico; evitar skill "faz tudo".
- `description` precisa dizer quando usar e quando nao usar, com gatilho objetivo.
- Preferir instrucoes em `SKILL.md`; script somente quando adicionar determinismo real.
- Se a skill for reutilizada por outros repos/time, planejar empacotamento como plugin.

## Definicao de pronto

- Codigo compila/executa no contexto esperado.
- Testes relevantes passam.
- Lint/format relevantes passam.
- Diff revisado com checklist de [code_review.md](./code_review.md).
- Risco residual e limites documentados quando houver.

## Checklists e templates

- Prompt de tarefa: [docs/CODEX_TASK_TEMPLATE.md](./docs/CODEX_TASK_TEMPLATE.md)
- Review padrao: [code_review.md](./code_review.md)
- Plano para tarefas longas: [PLANS.md](./PLANS.md)
- Skills operacionais: [docs/SKILLS_ADOPTION_PLAYBOOK.md](./docs/SKILLS_ADOPTION_PLAYBOOK.md)
- Adocao das melhores praticas: [docs/CODEX_BEST_PRACTICES_ADOPTION.md](./docs/CODEX_BEST_PRACTICES_ADOPTION.md)

## Melhoria continua

- Se o agente repetir o mesmo erro duas vezes, registrar retrospectiva e atualizar este arquivo.
- Preferir regras curtas e testaveis; mover detalhes grandes para documentos referenciados.
