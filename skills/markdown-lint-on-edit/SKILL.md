---
name: markdown-lint-on-edit
description: Aplica markdownlint automaticamente em arquivos .md criados/editados. Use quando criar ou editar documentação Markdown e quiser feedback imediato de lint.
---

# Markdown Lint on Edit — Phicube

Executa lint em Markdown com `markdownlint` logo após edição/salvamento de arquivo `.md`.

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

### 3) Watch (automático ao salvar)

Inicia watcher que observa alterações `.md` e executa lint por arquivo assim que houver mudança.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/markdown/watch_markdown_lint.ps1
```

Parar watcher: `Ctrl+C`

## Critério de pronto

- [ ] `markdownlint` executado no(s) arquivo(s) alterado(s)
- [ ] Erros reportados e/ou corrigidos antes de seguir
- [ ] Documentação sem violações de lint no escopo alterado

