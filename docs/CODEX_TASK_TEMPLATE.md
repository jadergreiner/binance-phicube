# Template de Pedido para Codex

Use este formato para aumentar qualidade e reduzir retrabalho.

## Modelo curto (copiar e preencher)

```text
Goal:
- O que precisa ser construido/corrigido

Context:
- Arquivos/pastas relevantes
- Logs/erros ou comportamento observado

Constraints:
- Padrões obrigatorios (arquitetura, seguranca, estilo, sem quebrar API etc.)
- Limites de escopo (o que nao mexer)

Done when:
- Evidencias objetivas de conclusao (testes, comportamento, diff, docs)
```

## Selecao de modo (obrigatorio)

- Use execucao direta quando a mudanca for local, curta e com baixo risco.
- Use `/plan` ou `PLANS.md` quando houver ambiguidade, varios modulos ou trade-off.
- Se nao houver criterio de pronto verificavel, a tarefa ainda nao esta pronta para execucao.

## Puxao de orelha (anti-padroes)

- Pedido ruim: "arruma isso ai" sem erro, sem arquivo, sem criterio de pronto.
- Pedido ruim: pedir mudanca grande sem planejar (`/plan` ou `PLANS.md`).
- Pedido ruim: misturar muitas demandas sem priorizacao.
- Pedido ruim: liberar permissao total sem necessidade comprovada.
- Pedido ruim: repetir no prompt regras que deveriam estar em `AGENTS.md`.
- Pedido ruim: pedir automacao de rotina que ainda falha na execucao manual.

## Quando usar plano antes de codar

- Task multi-modulo.
- Requisito ambiguo ou com trade-off de arquitetura.
- Correcao de bug intermitente sem reproducao clara.

Nesses casos, comece com `/plan` e so depois implemente.
