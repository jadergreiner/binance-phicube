# code_review.md

Checklist de review para usar com `/review` ou revisao manual de diff.

## Correção funcional

- O comportamento pedido foi implementado sem quebrar fluxos existentes?
- Existem regressões em caminhos de erro, timeout, retry ou reconexao?
- Mudancas em contratos (API, eventos, schemas) estao refletidas em consumidores?

## Testes e validacao

- Testes novos/ajustados cobrem caminho feliz, erro e borda?
- Suite relevante foi executada e teve sucesso?
- Lint/format foram executados nos arquivos alterados?

## Seguranca e operacao

- Segredos nao foram introduzidos em codigo, logs ou fixtures?
- Mudancas em Docker/env/permissoes tem impacto de risco documentado?
- Logs sao uteis para diagnostico sem vazar dados sensiveis?

## Qualidade de mudanca

- Diff esta focado, sem mudancas acidentais?
- Nomes, comentarios e docs estao claros e coerentes com o dominio?
- Existe rollback simples ou mitigacao caso a mudanca falhe?
