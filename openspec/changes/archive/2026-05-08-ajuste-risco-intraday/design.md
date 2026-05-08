## Context

`ajuste-risco-intraday` foi criada antes da padronização OpenSpec oficial e permaneceu em estado de scaffold. O requisito funcional correspondente foi desenvolvido e validado na change `intraday-loss-limit-10pct`, já com spec/tarefas/testes e integração no runtime.

## Goals / Non-Goals

**Goals:**
- Encerrar esta change sem duplicar implementação.
- Preservar rastreabilidade entre mudança legada e mudança final implementada.
- Impedir que conteúdo placeholder seja promovido para `openspec/specs`.

**Non-Goals:**
- Implementar código adicional.
- Alterar comportamento já entregue em `intraday-loss-limit-10pct`.

## Decisions

- Decisão 1: Marcar a change como superseded por `intraday-loss-limit-10pct`.
  - Racional: evitar duplicidade de escopo e conflito de governança.
- Decisão 2: Arquivar `ajuste-risco-intraday` com `--skip-specs`.
  - Racional: delta atual é placeholder e não deve virar spec oficial.

## Risks / Trade-offs

- [Risco] Falha de rastreabilidade entre o rascunho antigo e entrega final.
  -> Mitigação: manter referência explícita à `intraday-loss-limit-10pct` em proposal/design/tasks.
- [Trade-off] Histórico fica dividido em duas changes.
  -> Mitigação: preservar ambos os registros com relação de supersedência.
