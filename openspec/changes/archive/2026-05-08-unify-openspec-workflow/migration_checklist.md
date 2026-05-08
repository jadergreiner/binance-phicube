# Checklist de Migracao — Fluxo OpenSpec Oficial

Objetivo: reconciliar changes iniciadas fora do fluxo oficial antes de `apply`.

## Passos obrigatorios

- [x] Confirmar que a change existe em `openspec/changes/<change>/`.
- [x] Validar status de artefatos com `openspec status --change <change> --json`.
- [x] Garantir que `proposal.md`, `design.md`, `specs/` e `tasks.md` estao na estrutura oficial.
- [x] Executar `openspec validate --type change <change>`.
- [x] Registrar nota de migracao ou excecao na propria change.

## Criterio de saida

- Change pronta para fluxo oficial (`/opsx:apply`) sem dependencia operacional do compat local.
