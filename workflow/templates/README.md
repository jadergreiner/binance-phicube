# Templates do Workflow dev-cycle-v3

Este diretório padroniza os artefatos usados no fluxo [workflow/dev-cycle.yaml](../dev-cycle.yaml).

## Mapeamento etapa -> template

| Etapa | Responsável | Template | Saída esperada |
|---|---|---|---|
| `REFINEMENT_PLAN` | Time A | `plan.template.md` | `plan.md` |
| `REFINEMENT_TASKS` | Time A | `tasks.template.json` | `tasks.json` |
| `STATUS_UPDATE` | Time B | `tasks_status.template.json` | `tasks_status.json` |
| `STATUS_UPDATE` | Time B | `spec_status_update.template.md` | `spec_status_update.md` |

## Como usar

1. Copie o template correspondente para o artefato final da etapa.
2. Preencha todos os campos obrigatórios.
3. Mantenha rastreabilidade por `spec_id` e `task_id`.
4. Em `STATUS_UPDATE`, atualize tanto `tasks_status.json` quanto `spec_status_update.md`.

## Convenções

- `spec_id` deve seguir o padrão `SPEC_NNN`.
- `task_id` deve seguir o padrão `task_###`.
- Datas devem estar em formato ISO 8601 (`YYYY-MM-DD` ou `YYYY-MM-DDTHH:MM:SSZ`).
- Sempre registrar evidências (diagnóstico, testes e arquivos alterados).

## Checklist rápido por execução

- [ ] `plan.md` gerado a partir de `plan.template.md`
- [ ] `tasks.json` gerado a partir de `tasks.template.json`
- [ ] Implementação concluída pelo Time B
- [ ] `tasks_status.json` atualizado
- [ ] `spec_status_update.md` atualizado
