# Instruções do Projeto — Binance Phicube

## Objetivo

Este arquivo define regras operacionais complementares para uso do Codex no repositório Binance Phicube.
O objetivo é garantir execução consistente, segura e verificável em tarefas de desenvolvimento.

## Precedência de Instruções

Ordem de prioridade para resolução de conflitos:

1. `AGENTS.md` (fonte primária do repositório)
2. `.codex/codex-instructions.md` (complemento operacional)
3. Prompt da tarefa atual (escopo específico, sem contrariar os itens anteriores)

## Idioma e Exceções

Idioma padrão: Português do Brasil (pt-BR) para comunicação, documentação e textos operacionais produzidos no projeto.

Aplicações padrão em pt-BR:
- Respostas e explicações no chat
- Comentários e docstrings no código
- Mensagens de log e erro voltadas ao operador
- Arquivos de documentação (`.md`)
- Descrições textuais em testes (quando aplicável)

Exceções técnicas permitidas:
- Mensagens de commit em inglês (Conventional Commits)
- Identificadores técnicos de código (nomes de variáveis, funções, classes, tipos, APIs)
- Mensagens brutas de bibliotecas, stack traces e erros não controláveis pelo projeto

## Regras de Execução

- Em mudanças complexas, planejar antes de codar (modo plano ou `PLANS.md`).
- Em mudanças simples e locais, implementar direto e validar rapidamente.
- Não expor segredos em logs, documentação, testes ou commits.
- Manter menor privilégio possível de execução (sandbox/aprovações), com exceções justificadas.

## Uso de Skills e MCP

- Usar skills quando houver aderência objetiva entre a tarefa e o `description` da skill.
- Evitar skill fora de escopo ou genérica quando uma execução direta for mais simples e segura.
- Usar MCP quando ele agregar contexto verificável e reduzir ambiguidade.
- Quando MCP não agregar valor prático para a tarefa, operar diretamente no código/repositório local.

## Qualidade e Done When

Para tarefas com alteração de código, mínimo esperado:

- Executar testes relevantes para o escopo alterado.
- Executar `ruff check` e `ruff format` quando aplicável.
- Declarar critério de pronto (done when) alinhado ao `AGENTS.md`.

Condição de pronto:
- Código executa no contexto esperado.
- Validações essenciais passaram.
- Riscos residuais e limites foram explicitados quando houver.

## Referências

- `AGENTS.md`
- `docs/CODEX_TASK_TEMPLATE.md`
- `code_review.md`
- `PLANS.md`
