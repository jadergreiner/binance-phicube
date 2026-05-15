---
name: markdown-lint-on-edit
description: Aplica markdownlint automaticamente em arquivos .md criados/editados. Use quando criar ou editar documentação Markdown e quiser feedback imediato de lint.
---

# Markdown Lint on Edit — Phicube

Executa lint em Markdown com `markdownlint` logo após edição/salvamento de arquivo `.md`.
Para arquivos de `openspec/changes/*`, também executa validação estrutural com
`openspec validate`, pois o lint de Markdown não cobre regras de delta/spec.

## Quando usar

- Após criar qualquer arquivo `.md`
- Após editar docs em `openspec/`, `docs/`, `README.md`, `AGENTS.md`
- Antes de commitar documentação

## Pré-requisito

- `markdownlint` disponível no PATH

Validação rápida:

```powershell
markdownlint --version
```

## Modos de execução

### 1) One-shot (arquivos alterados)

Roda lint apenas nos arquivos `.md` modificados no git.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/markdown/lint_markdown.ps1 -Mode changed
```

### 2) One-shot (arquivo específico)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/markdown/lint_markdown.ps1 -Path openspec/changes/order-monitor-consistency-hardening/specs/order-monitor-reconciliation/spec.md
```

### 2.1) OpenSpec (arquivo + validação do change)

Use este modo para artefatos em `openspec/changes/<change-id>/...`:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/markdown/lint_markdown.ps1 -Path openspec/changes/spec-040-serializable-protocol/proposal.md -OpenSpecChange spec-040-serializable-protocol
```

### 3) Watch (automático ao salvar)

Inicia watcher que observa alterações `.md` e executa lint por arquivo assim que houver mudança.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/markdown/watch_markdown_lint.ps1
```

Parar watcher: `Ctrl+C`

## Critério de pronto

- [ ] `markdownlint` executado no(s) arquivo(s) alterado(s)
- [ ] Se houver alteração em `openspec/changes/*`, `openspec validate <change-id>` executado
- [ ] Erros reportados e/ou corrigidos antes de seguir
- [ ] Documentação sem violações de lint no escopo alterado
